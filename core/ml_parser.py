import re
import threading

from core.ocr import extract_text_from_file, file_to_first_image
from core.parser import parse_receipt

MODEL_ID = "naver-clova-ix/donut-base-finetuned-cord-v2"
TASK_PROMPT = "<s_cord-v2>"

_model = None
_processor = None
_model_lock = threading.Lock()


def _load_model():
    global _model, _processor
    if _model is not None:
        return _model, _processor
    with _model_lock:
        if _model is not None:
            return _model, _processor
        from transformers import DonutProcessor, VisionEncoderDecoderModel
        import torch
        _processor = DonutProcessor.from_pretrained(MODEL_ID)
        _model = VisionEncoderDecoderModel.from_pretrained(MODEL_ID)
        _model.eval()
        if torch.cuda.is_available():
            _model = _model.to("cuda")
    return _model, _processor


def _run_donut(image):
    import torch
    model, processor = _load_model()
    device = next(model.parameters()).device

    pixel_values = processor(image, return_tensors="pt").pixel_values.to(device)
    decoder_input_ids = processor.tokenizer(
        TASK_PROMPT, add_special_tokens=False, return_tensors="pt"
    ).input_ids.to(device)

    with torch.no_grad():
        outputs = model.generate(
            pixel_values,
            decoder_input_ids=decoder_input_ids,
            max_length=model.decoder.config.max_position_embeddings,
            early_stopping=True,
            pad_token_id=processor.tokenizer.pad_token_id,
            eos_token_id=processor.tokenizer.eos_token_id,
            use_cache=True,
            num_beams=1,
            bad_words_ids=[[processor.tokenizer.unk_token_id]],
            return_dict_in_generate=True,
        )

    sequence = processor.batch_decode(outputs.sequences)[0]
    sequence = sequence.replace(processor.tokenizer.eos_token, "").replace(
        processor.tokenizer.pad_token, ""
    )
    sequence = re.sub(r"<.*?>", "", sequence, count=1).strip()
    return processor.token2json(sequence)


def _extract_cord_fields(cord_dict):
    """Pull Items and Amount out of a CORD-v2 prediction dict."""
    items = []
    menu = cord_dict.get("menu", [])
    if isinstance(menu, dict):
        menu = [menu]
    for entry in menu:
        name = entry.get("nm", "").strip()
        price = entry.get("price", "").strip()
        if name or price:
            items.append(f"{name} {price}".strip())

    amount = ""
    total_block = cord_dict.get("total", {})
    if isinstance(total_block, dict):
        amount = total_block.get("total_price", "").strip()

    return items, amount


def parse_receipt_ml(filepath):
    """
    Parse a receipt file using Donut CORD-v2 for Items/Amount and
    improved regex for Company/Date/Payment Method.

    Returns:
        (parsed_dict, ocr_text)
    """
    ocr_text = extract_text_from_file(filepath)

    try:
        image = file_to_first_image(filepath)
        cord_dict = _run_donut(image)

        items, amount = _extract_cord_fields(cord_dict)

        # Regex parse for Company / Date / Payment Method
        regex_parsed = parse_receipt(ocr_text)

        parsed = {
            "Company": regex_parsed["Company"],
            "Date": regex_parsed["Date"],
            "Items": "; ".join(items) if items else regex_parsed["Items"],
            "Amount": amount if amount else regex_parsed["Amount"],
            "Payment Method": regex_parsed["Payment Method"],
        }
        return parsed, ocr_text

    except Exception as e:
        print(f"[ml_parser] Donut inference failed, falling back to regex: {e}")
        return parse_receipt(ocr_text), ocr_text

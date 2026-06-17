"""
DarkHubFreepikStudio — ComfyUI node for Seedream 4.5 Edit via kie.ai API,
with optional support for any OpenAI-compatible image generation API
(/v1/images/generations).
"""
import os, io, time, base64, json, logging
import requests
import torch
import numpy as np
from PIL import Image

log = logging.getLogger("darkhub_seedream45")

KIE_BASE = "https://api.kie.ai"
SEEDREAM_MODEL = "seedream/4.5-edit"

ASPECT_RATIOS = [
    "Traditional: 3:4", "Square: 1:1", "Widescreen: 16:9",
    "Portrait: 2:3", "Landscape: 3:2", "Tall: 9:16",
    "Classic: 4:3", "Ultra Wide: 21:9",
]
RATIO_MAP = {
    "Traditional: 3:4": "3:4",
    "Square: 1:1": "1:1",
    "Widescreen: 16:9": "16:9",
    "Portrait: 2:3": "2:3",
    "Landscape: 3:2": "3:2",
    "Tall: 9:16": "9:16",
    "Classic: 4:3": "4:3",
    "Ultra Wide: 21:9": "21:9",
}

# OpenAI-compatible size mapping from aspect ratio
OPENAI_SIZE_MAP = {
    "Square: 1:1": "1024x1024",
    "Widescreen: 16:9": "1792x1024",
    "Portrait: 2:3": "1024x1536",
    "Landscape: 3:2": "1536x1024",
    "Tall: 9:16": "1024x1792",
    "Traditional: 3:4": "1024x1365",
    "Classic: 4:3": "1365x1024",
    "Ultra Wide: 21:9": "1792x768",
}

MODELS = [
    "Seedream v4.5 Edit",
    "Seedream v4.5 T2I",
    "Seedream v5.0 Lite",
]
MODEL_MAP = {
    "Seedream v4.5 Edit":  "seedream/4.5-edit",
    "Seedream v4.5 T2I":   "seedream/4.5",
    "Seedream v5.0 Lite":  "seedream/5.0-lite",
}

# OpenAI-compatible quality options
OPENAI_QUALITY = ["auto", "standard", "hd"]
OPENAI_STYLE = ["vivid", "natural"]


def _tensor_to_b64(tensor: torch.Tensor) -> str:
    """Convert ComfyUI IMAGE tensor [B,H,W,C] float32 → base64 JPEG."""
    arr = (tensor[0].cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr, "RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    return base64.b64encode(buf.getvalue()).decode()


def _b64_to_tensor(b64: str) -> torch.Tensor:
    """Convert base64 image → ComfyUI IMAGE tensor [1,H,W,C]."""
    data = base64.b64decode(b64)
    img = Image.open(io.BytesIO(data)).convert("RGB")
    arr = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(arr).unsqueeze(0)


def _url_to_tensor(url: str) -> torch.Tensor:
    """Download image from URL → ComfyUI IMAGE tensor."""
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    arr = np.array(img).astype(np.float32) / 255.0
    return torch.from_numpy(arr).unsqueeze(0)


def _generate_openai(base_url, api_key, model_name, prompt, aspect_ratio,
                     num_images, quality, style_name, seed):
    """Call any OpenAI-compatible /v1/images/generations endpoint."""
    base_url = base_url.rstrip("/")
    url = f"{base_url}/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    size = OPENAI_SIZE_MAP.get(aspect_ratio, "1024x1024")
    body = {
        "model": model_name,
        "prompt": prompt,
        "n": num_images,
        "size": size,
        "response_format": "b64_json",
    }
    if quality != "auto":
        body["quality"] = quality
    if style_name:
        body["style"] = style_name
    if seed:
        body["seed"] = seed

    log.info(f"[darkHUB] OpenAI API → {url} model={model_name} size={size}")
    r = requests.post(url, headers=headers, json=body, timeout=120)
    r.raise_for_status()
    resp = r.json()

    tensors = []
    urls = []
    for item in resp.get("data", []):
        if item.get("b64_json"):
            tensors.append(_b64_to_tensor(item["b64_json"]))
            urls.append("")
        elif item.get("url"):
            tensors.append(_url_to_tensor(item["url"]))
            urls.append(item["url"])

    return tensors, urls, resp


class DarkHubFreepikStudio:
    """Seedream 4.5 image generation/editing via kie.ai API,
    or any OpenAI-compatible image generation API."""

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model":           (MODELS, {"default": "Seedream v4.5 Edit"}),
                "prompt":          ("STRING", {"multiline": True, "default": "beautiful portrait"}),
                "negative_prompt": ("STRING", {"multiline": True, "default": "watermark, blur, low quality"}),
                "style":           ("STRING", {"multiline": False, "default": ""}),
                "aspect_ratio":    (ASPECT_RATIOS, {"default": "Traditional: 3:4"}),
                "seed":            ("INT",   {"default": 0, "min": 0, "max": 2147483647}),
                "control_after_generate": (["fixed", "randomize", "increment", "decrement"], {"default": "fixed"}),
                "nsfw":            ("BOOLEAN", {"default": False}),
                "timeout":         ("INT",   {"default": 240, "min": 30, "max": 600}),
                "num_images":      ("INT",   {"default": 2, "min": 1, "max": 4}),
                "output_prefix":   ("STRING", {"default": "darkhub_seedream45"}),
                "api_key":         ("STRING", {"default": ""}),
                # OpenAI-compatible provider settings (leave empty to use kie.ai)
                "openai_api_base": ("STRING", {"default": "", "multiline": False,
                                               "placeholder": "https://api.openai.com  (empty = use kie.ai)"}),
                "openai_model":    ("STRING", {"default": "", "multiline": False,
                                               "placeholder": "dall-e-3 / gpt-image-1 / ..."}),
                "openai_quality":  (OPENAI_QUALITY, {"default": "auto"}),
                "openai_style":    (["(none)"] + OPENAI_STYLE, {"default": "(none)"}),
            },
            "optional": {
                "reference_image_1": ("IMAGE",),
                "reference_image_2": ("IMAGE",),
                "reference_image_3": ("IMAGE",),
                "reference_image_4": ("IMAGE",),
                "reference_image_5": ("IMAGE",),
            }
        }

    RETURN_TYPES = ("IMAGE", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("images", "task_id", "status", "image_urls_json", "saved_paths_json", "task_json", "metadata_path", "summary")
    FUNCTION = "generate"
    CATEGORY = "darkHUB"

    def generate(self, model, prompt, negative_prompt, style, aspect_ratio, seed,
                 control_after_generate, nsfw, timeout, num_images, output_prefix, api_key,
                 openai_api_base, openai_model, openai_quality, openai_style,
                 reference_image_1=None, reference_image_2=None,
                 reference_image_3=None, reference_image_4=None,
                 reference_image_5=None):

        key = api_key.strip() or os.environ.get("KIE_API_KEY", "44f4c847e4b8a123441b0891322acb9b")
        effective_seed = seed if control_after_generate == "fixed" else None

        # Route to OpenAI-compatible API if base URL is provided
        if openai_api_base.strip():
            oai_key = api_key.strip() or os.environ.get("OPENAI_API_KEY", "")
            oai_model = openai_model.strip() or "dall-e-3"
            oai_style = openai_style if openai_style != "(none)" else ""
            try:
                tensors, urls, resp = _generate_openai(
                    base_url=openai_api_base.strip(),
                    api_key=oai_key,
                    model_name=oai_model,
                    prompt=prompt,
                    aspect_ratio=aspect_ratio,
                    num_images=num_images,
                    quality=openai_quality,
                    style_name=oai_style,
                    seed=effective_seed,
                )
            except Exception as e:
                log.error(f"[darkHUB] OpenAI API error: {e}")
                blank = torch.zeros(1, 512, 512, 3)
                return (blank, "error", str(e), "[]", "[]", "{}", "", str(e))

            if not tensors:
                blank = torch.zeros(1, 512, 512, 3)
                return (blank, "openai", "no_images", "[]", "[]", json.dumps(resp), "", "No images returned")

            out = torch.cat(tensors, dim=0)
            summary = f"Generated {len(tensors)} image(s) via {oai_model} [{OPENAI_SIZE_MAP.get(aspect_ratio, '1024x1024')}]"
            log.info(f"[darkHUB] OpenAI done: {len(tensors)} images")
            return (out, "openai", "COMPLETED", json.dumps(urls), json.dumps(urls),
                    json.dumps(resp), "", summary)

        # --- kie.ai backend (default) ---
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        api_model = MODEL_MAP.get(model, SEEDREAM_MODEL)
        ratio = RATIO_MAP.get(aspect_ratio, "3:4")

        # Collect reference images as base64 data URIs
        ref_images = []
        for img_tensor in [reference_image_1, reference_image_2, reference_image_3,
                            reference_image_4, reference_image_5]:
            if img_tensor is not None:
                b64 = _tensor_to_b64(img_tensor)
                ref_images.append(f"data:image/jpeg;base64,{b64}")

        body = {
            "model": api_model,
            "input": {
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "aspect_ratio": ratio,
                "nsfw_checker": nsfw,
                "seed": effective_seed,
            }
        }
        if style:
            body["input"]["style"] = style
        if ref_images:
            body["input"]["image_urls"] = ref_images
        if num_images > 1:
            body["input"]["n"] = num_images

        body["input"] = {k: v for k, v in body["input"].items() if v is not None}

        log.info(f"[darkHUB] Calling kie.ai model={api_model} ratio={ratio} refs={len(ref_images)}")

        try:
            r = requests.post(f"{KIE_BASE}/api/v1/jobs/createTask",
                              headers=headers, json=body, timeout=30)
            r.raise_for_status()
            resp = r.json()
        except Exception as e:
            log.error(f"[darkHUB] API error: {e}")
            blank = torch.zeros(1, 512, 512, 3)
            return (blank, "error", str(e), "[]", "[]", "{}", "", str(e))

        if resp.get("code") != 200:
            err = str(resp)
            log.error(f"[darkHUB] API returned error: {err}")
            blank = torch.zeros(1, 512, 512, 3)
            return (blank, "error", err, "[]", "[]", json.dumps(resp), "", err)

        task_id = resp["data"]["taskId"]
        log.info(f"[darkHUB] Task created: {task_id}")

        poll_url = f"{KIE_BASE}/api/v1/jobs/getTaskDetail?taskId={task_id}"
        status = "pending"
        result_data = {}
        for _ in range(timeout // 3):
            time.sleep(3)
            try:
                pr = requests.get(poll_url, headers=headers, timeout=15)
                if not pr.ok:
                    continue
                pd = pr.json()
                status = pd.get("data", {}).get("status", "pending")
                if status in ("COMPLETED", "SUCCESS", "success", "completed"):
                    result_data = pd.get("data", {})
                    break
                if status in ("FAILED", "ERROR", "failed", "error"):
                    log.error(f"[darkHUB] Task failed: {pd}")
                    blank = torch.zeros(1, 512, 512, 3)
                    return (blank, task_id, status, "[]", "[]", json.dumps(pd), "", "Task failed")
            except Exception as e:
                log.warning(f"[darkHUB] Poll error: {e}")
                continue

        image_urls = (result_data.get("output", {}).get("images") or
                      result_data.get("imageUrls") or
                      result_data.get("image_urls") or [])
        if isinstance(image_urls, str):
            image_urls = [image_urls]

        image_urls_json = json.dumps(image_urls)

        if not image_urls:
            log.error(f"[darkHUB] No images in result: {result_data}")
            blank = torch.zeros(1, 512, 512, 3)
            return (blank, task_id, status, "[]", "[]", json.dumps(result_data), "", "No images")

        tensors = []
        saved = []
        for url in image_urls:
            try:
                t = _url_to_tensor(url)
                tensors.append(t)
                saved.append(url)
            except Exception as e:
                log.error(f"[darkHUB] Failed to download {url}: {e}")

        if not tensors:
            blank = torch.zeros(1, 512, 512, 3)
            return (blank, task_id, status, image_urls_json, "[]", json.dumps(result_data), "", "Download failed")

        out = torch.cat(tensors, dim=0)
        saved_json = json.dumps(saved)
        task_json = json.dumps(result_data)
        summary = f"Generated {len(tensors)} image(s) via {api_model} [{ratio}] seed={seed}"

        log.info(f"[darkHUB] Done: {len(tensors)} images")
        return (out, task_id, status, image_urls_json, saved_json, task_json, "", summary)


NODE_CLASS_MAPPINGS = {
    "DarkHubFreepikStudio": DarkHubFreepikStudio,
}
NODE_DISPLAY_NAME_MAPPINGS = {
    "DarkHubFreepikStudio": "darkHUB Seedream 4.5 Studio",
}

import os
import json
import streamlit as st
from dashscope import MultiModalConversation, Generation
import dashscope

# --- Configuration ---
# Ensure API Key is available
if "DASHSCOPE_API_KEY" in st.secrets:
    dashscope.api_key = st.secrets["DASHSCOPE_API_KEY"]

from PIL import Image

def analyze_image_with_qwen(image_path, context_text=""):
    """
    Analyzes image using Qwen-VL-Plus to detect people and describe them, 
    incorporating user-provided context clues. Returns cropped face images if possible.
    """
    abs_path = os.path.abspath(image_path)
    file_url = f"file://{abs_path}"

    prompt_text = f'''请分析这张图片中的人物。
    用户提供的线索是："{context_text}"
    
    任务：
    1. 识别图中的所有人脸/人物。
    2. 结合用户的线索（方位、衣着、特征）和已有的人脸特征，尝试推断这个人的名字。
    3. 如果线索中没提到，或者无法确定，"suggested_name" 设为 null。
    4. 提供每个人物在图中的边界框 (box_2d)，格式为 [ymin, xmin, ymax, xmax] (归一化 0-1000)。
    
    对于每一个检测到的人，请返回 JSON 对象，包含：
    - description: 简短的视觉描述。
    - suggested_name: 推断的名字（如果有）。
    - confidence_reason: 推断的理由。
    - box_2d: [ymin, xmin, ymax, xmax]
    
    重要：请严格按照 JSON 列表格式返回结果。
    '''

    messages = [{
        'role': 'user',
        'content': [
            {'image': file_url},
            {'text': prompt_text}
        ]
    }]

    try:
        response = MultiModalConversation.call(model='qwen-vl-plus', messages=messages)
        if response.status_code == 200:
            content = _extract_text_from_qwen_response(response)
            results = _parse_json_safely(content)
            
            # Post-process: Crop faces
            try:
                original_img = Image.open(image_path)
                width, height = original_img.size
                
                for res in results:
                    if 'box_2d' in res:
                        # Qwen-VL uses [ymin, xmin, ymax, xmax] with 0-1000 scale
                        box = res['box_2d']
                        ymin, xmin, ymax, xmax = box
                        
                        left = (xmin / 1000) * width
                        top = (ymin / 1000) * height
                        right = (xmax / 1000) * width
                        bottom = (ymax / 1000) * height
                        
                        # Add margin? Maybe a little.
                        # Crop
                        cropped = original_img.crop((left, top, right, bottom))
                        res['cropped_face'] = cropped
            except Exception as e:
                print(f"Cropping failed: {e}")
                
            return results
            
        return [{"error": f"API Error: {response.code} - {response.message}"}]
    except Exception as e:
        return [{"error": f"Analysis failed: {str(e)}"}]

def analyze_text_diary(text):
    """
    Analyzes text diary using Qwen-Plus (LLM) to extract entities and relationships.
    """
    prompt = f"""
    分析这篇日记内容："{text}"
    
    请提取其中提到的人名（不包含"我"）。
    对于每个人，推断其与作者（"Me"）的关系（如：朋友、老师、同事、陌生人）。
    
    返回 JSON 列表格式：
    [
        {{"name": "老王", "relation": "邻居", "description": "根据文本提取的特征或上下文"}}
    ]
    如果没有提到其他人，返回 []。
    """
    
    try:
        response = Generation.call(model='qwen-plus', prompt=prompt, result_format='message')
        if response.status_code == 200:
            content = response.output.choices[0].message.content
            return _parse_json_safely(content)
        return []
    except Exception as e:
        return [{"error": str(e)}]

def find_best_match(new_description, known_nodes):
    """
    Uses LLM to match a new visual/text description against known nodes.
    Returns: {"match_found": bool, "suggested_id": str, "suggested_name": str, "reason": str}
    """
    if not known_nodes:
        return {"match_found": False}
        
    # Simplify nodes for token efficiency
    known_summary = []
    for n in known_nodes:
        if n['id'] == 'root_me': continue
        desc = n.get('description', '') or "无详细描述"
        known_summary.append(f"ID: {n['id']}, Name: {n['name']}, Known Traits: {desc}")
    
    prompt = f"""
    我有一个新检测到的人物描述："{new_description}"
    
    这是我记忆库里已有的熟人：
    {json.dumps(known_summary, ensure_ascii=False)}
    
    任务：判断这个新描述是否极有可能是已有的某个人？
    如果是，返回 JSON: {{"match_found": true, "suggested_id": "...", "reason": "..."}}
    如果不像任何人，返回: {{"match_found": false}}
    
    只返回 JSON。
    """
    
    try:
        response = Generation.call(model='qwen-plus', prompt=prompt, result_format='message')
        if response.status_code == 200:
            content = response.output.choices[0].message.content
            result = _parse_json_safely(content)
            
            # If result is list (sometimes LLM does that), take first
            if isinstance(result, list) and len(result) > 0:
                result = result[0]
            
            # Enrich with name for UI convenience
            if result.get("match_found"):
                for n in known_nodes:
                    if n['id'] == result['suggested_id']:
                        result['suggested_name'] = n['name']
                        break
            return result
            
        return {"match_found": False}
    except Exception:
        return {"match_found": False}

def _extract_text_from_qwen_response(response):
    # Qwen-VL content extraction helper
    content_list = response.output.choices[0].message.content
    text_content = ""
    for item in content_list:
        if 'text' in item:
            text_content += item['text']
    return text_content

def _parse_json_safely(text):
    text = text.strip()
    if text.startswith("```json"): text = text[7:]
    if text.startswith("```"): text = text[3:]
    if text.endswith("```"): text = text[:-3]
    try:
        data = json.loads(text.strip())
        if isinstance(data, dict): return [data] # normalization
        return data
    except:
        return []

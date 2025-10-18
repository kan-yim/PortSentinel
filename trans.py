import os
import json
from typing import List, Dict, Optional
from dotenv import load_dotenv

# 确保导入路径正确
from langchain_community.document_loaders import Docx2txtLoader
from langchain_core.documents import Document

# --- Configuration ---
DOCX_PATH = "Knowledge Base.docx"
OUTPUT_JSON_PATH = "knowledge_base_structured.json"

# --- Load Environment Variables ---
load_dotenv()

# --- SOP Parsing Logic ---

SECTION_HEADERS = {"Overview", "Preconditions", "Resolution", "Verification"}


def normalize_module(module_field: Optional[str]) -> str:
    """
    直接使用表格中的 Module 字段值作为模块名称。
    如果为空或无效，返回 "Unknown"。
    """
    if not module_field:
        return "Unknown"
    
    # 清理并返回模块字段的值
    module_cleaned = module_field.strip()
    
    if not module_cleaned:
        return "Unknown"
    
    return module_cleaned


def extract_sop_blocks(doc_content: str) -> List[str]:
    """
    通过查找"Module"标记，把文档切分成 SOP 级别的块。
    支持标题换行或模块缩写拼写错误的情况。
    """
    lines = doc_content.split('\n')
    module_indices = [idx for idx, line in enumerate(lines) if line.strip().lower() == "module"]
    if not module_indices:
        return []

    block_starts: List[int] = []
    for module_idx in module_indices:
        # 回溯查找标题起始位置（可能跨多行）
        title_idx = module_idx - 1
        while title_idx >= 0 and not lines[title_idx].strip():
            title_idx -= 1

        start = max(title_idx, 0)
        while (
            start - 1 >= 0
            and lines[start - 1].strip()
            and lines[start - 1].strip() not in SECTION_HEADERS
        ):
            start -= 1

        block_starts.append(start)

    blocks: List[str] = []
    for i, start in enumerate(block_starts):
        end = block_starts[i + 1] if i + 1 < len(block_starts) else len(lines)
        block_lines = lines[start:end]
        block_text = "\n".join(block_lines).strip()
        if block_text:
            blocks.append(block_text)
    return blocks


def parse_sop_section(sop_text: str) -> Dict[str, Optional[str]]:
    """
    将单个 SOP 文本块解析为包含标题和标准部分的字典。
    """
    sop_data = {
        "Title": None,
        "Overview": None,
        "Preconditions": None,
        "Resolution": None,
        "Verification": None,
        "Module": None
    }
    raw_lines = sop_text.split('\n')
    lines = [line.rstrip() for line in raw_lines]
    stripped_lines = [line.strip() for line in lines]
    if not any(stripped_lines):
        return sop_data

    section_positions = {}
    for idx, value in enumerate(stripped_lines):
        lower_value = value.lower()
        if lower_value == "module":
            section_positions["Module"] = idx
        elif lower_value == "overview":
            section_positions["Overview"] = idx
        elif lower_value == "preconditions":
            section_positions["Preconditions"] = idx
        elif lower_value == "resolution":
            section_positions["Resolution"] = idx
        elif lower_value == "verification":
            section_positions["Verification"] = idx

    module_idx = section_positions.get("Module")
    if module_idx is not None:
        title_lines = [stripped_lines[i] for i in range(module_idx) if stripped_lines[i]]
        title = " ".join(title_lines).strip()
    else:
        title = stripped_lines[0] if stripped_lines else None
    sop_data["Title"] = title or None

    def extract_section(label: str) -> Optional[str]:
        start_idx = section_positions.get(label)
        if start_idx is None:
            return None
        subsequent_indices = [
            section_positions[key]
            for key in ["Module", "Overview", "Preconditions", "Resolution", "Verification"]
            if key in section_positions and section_positions[key] > start_idx
        ]
        end_idx = min(subsequent_indices) if subsequent_indices else len(lines)
        content = [
            lines[i].strip()
            for i in range(start_idx + 1, end_idx)
            if lines[i].strip()
        ]
        return "\n".join(content).strip() if content else None

    module_field = extract_section("Module")
    sop_data["Module"] = normalize_module(module_field)
    sop_data["Overview"] = extract_section("Overview")
    sop_data["Preconditions"] = extract_section("Preconditions")
    sop_data["Resolution"] = extract_section("Resolution")
    sop_data["Verification"] = extract_section("Verification")

    return sop_data


# --- Main Processing Function ---
def load_and_structure_knowledge_base() -> Optional[List[Dict[str, Optional[str]]]]:
    """
    加载知识库文档,按 SOP 分割,并将每个 SOP 解析为结构化字典列表。
    """
    print(f"Loading document from: {DOCX_PATH}")
    # 1. 加载文档
    try:
        loader = Docx2txtLoader(DOCX_PATH)
        docs = loader.load()
        if not docs:
            print("错误: 未加载任何文档。请检查文件路径和内容。")
            return None
        doc_content = docs[0].page_content
        print(f"文档加载成功。内容长度: {len(doc_content)} 字符。")
    except ModuleNotFoundError:
        print("错误: 缺少 'docx2txt' 模块。")
        print("请将其添加到 requirements.txt 并运行 'pip install -r requirements.txt'")
        return None
    except Exception as e:
        print(f"加载文档时出错: {e}")
        return None

    print("正在按 SOP 分割文档...")

    sop_blocks = extract_sop_blocks(doc_content)
    if not sop_blocks:
        print("错误: 未找到任何 SOP 块。")
        return None

    print(f"找到 {len(sop_blocks)} 个 SOP 块。")

    structured_sops = []

    for i, sop_text in enumerate(sop_blocks):
        print(f"\n正在解析 SOP 块 {i+1}...")
        sop_data = parse_sop_section(sop_text)

        if sop_data.get("Title"):
            structured_sops.append(sop_data)
            print(f"  成功解析标题: {sop_data['Title']}")
            print(f"  模块: {sop_data['Module']}")
        else:
            preview = sop_text.strip().split('\n', 1)[0]
            print(f"  警告: 未能解析 SOP 块 {i+1} 的有效标题,跳过此块。预览: {preview[:80]}")

    print(f"\n成功解析了 {len(structured_sops)} 个 SOP。")
    return structured_sops


# --- Save to JSON File ---
def save_to_json(data: List[Dict[str, Optional[str]]], file_path: str):
    """将解析后的数据保存到 JSON 文件。"""
    print(f"\n正在将解析结果保存到文件: {file_path}")
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print("文件保存成功！")
    except IOError as e:
        print(f"错误: 无法写入文件 {file_path}: {e}")
    except Exception as e:
        print(f"保存 JSON 时发生未知错误: {e}")


# --- Run the script ---
if __name__ == "__main__":
    doc_path = DOCX_PATH
    doc_dir = os.path.dirname(doc_path)
    doc_filename = os.path.basename(doc_path)

    # 检查文件是否存在
    if not os.path.exists(doc_path):
        print(f"错误: 文档未在 '{doc_path}' 找到。")
        if doc_dir and doc_dir != '.':
            print(f"--> 请确保 '{doc_filename}' 位于 '{doc_dir}' 目录下。 <--")
        else:
            print(f"--> 请确保 '{doc_filename}' 与脚本在同一目录下。 <--")
    else:
        # 文件存在，执行加载、分割和结构化解析
        parsed_data = load_and_structure_knowledge_base()

        if parsed_data:
            # 将结果保存到 JSON 文件
            save_to_json(parsed_data, OUTPUT_JSON_PATH)
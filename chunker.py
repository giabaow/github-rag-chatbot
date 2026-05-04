from langchain_community.text_splitters import RecursiveCharacterTextSplitter
 
# Language-aware separators split at logical code boundaries first
SEPARATORS_BY_EXT = {
    ".py":   ["\nclass ", "\ndef ", "\n\n", "\n", " "],
    ".js":   ["\nfunction ", "\nclass ", "\nconst ", "\n\n", "\n", " "],
    ".ts":   ["\nfunction ", "\nclass ", "\ninterface ", "\ntype ", "\n\n", "\n", " "],
    ".tsx":  ["\nexport ", "\nfunction ", "\nconst ", "\n\n", "\n", " "],
    ".jsx":  ["\nexport ", "\nfunction ", "\nconst ", "\n\n", "\n", " "],
    ".java": ["\nclass ", "\npublic ", "\nprivate ", "\n\n", "\n", " "],
    ".go":   ["\nfunc ", "\ntype ", "\n\n", "\n", " "],
    ".rs":   ["\nfn ", "\nstruct ", "\nimpl ", "\n\n", "\n", " "],
    ".md":   ["\n## ", "\n### ", "\n#### ", "\n\n", "\n"],
    ".html": ["\n<section", "\n<div", "\n<article", "\n\n", "\n"],
}
DEFAULT_SEPARATORS = ["\n\n", "\n", " ", ""]
 
 
def chunk_files(files: list[dict], chunk_size: int = 800,chunk_overlap: int = 100,) -> list[dict]:

    chunks = []
 
    for file in files:
        seps = SEPARATORS_BY_EXT.get(file["extension"], DEFAULT_SEPARATORS)
        splitter = RecursiveCharacterTextSplitter(
            separators=seps,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
 
        # Prepend file path to each chunk so the LLM always knows the source
        prefixed_content = f"# File: {file['path']}\n\n{file['content']}"
        parts = splitter.split_text(prefixed_content)
 
        for i, part in enumerate(parts):
            chunks.append({
                "text": part,
                "metadata": {
                    "file_path": file["path"],
                    "chunk_index": i,
                    "extension": file["extension"],
                },
            })
 
    print(f"Created {len(chunks)} chunks from {len(files)} files")
    return chunks
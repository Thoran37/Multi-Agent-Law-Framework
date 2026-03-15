import pytesseract
import fitz  # PyMuPDF
import logging
from pathlib import Path
from typing import List, Dict, Any
from io import BytesIO

logger = logging.getLogger(__name__)

# Make sure tesseract is installed: https://github.com/UB-Mannheim/tesseract/wiki
# Or install via package manager (e.g., apt-get install tesseract-ocr on Linux)

def extract_text_from_pdf_with_ocr(pdf_bytes: bytes) -> str:
    """
    Extract text from PDF using both PyPDF2 (for native text) and Tesseract OCR (for scanned images).
    Combine both results to get complete text.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = []

        for page_num, page in enumerate(doc):
            # First try to extract native text
            native_text = page.get_text()
            
            if native_text.strip():
                # If native text exists, use it
                full_text.append(f"--- Page {page_num + 1} (Native Text) ---\n{native_text}\n")
            else:
                # If no native text, use OCR
                try:
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
                    img_data = pix.tobytes("ppm")
                    ocr_text = pytesseract.image_to_string(BytesIO(img_data))
                    full_text.append(f"--- Page {page_num + 1} (OCR) ---\n{ocr_text}\n")
                    logger.info(f"OCR extracted text from page {page_num + 1}")
                except Exception as e:
                    logger.warning(f"OCR failed for page {page_num + 1}: {e}")
                    full_text.append(f"--- Page {page_num + 1} (Failed to extract) ---\n")

        doc.close()
        return "\n".join(full_text)

    except Exception as e:
        logger.exception(f"Error extracting text with OCR: {e}")
        raise


def build_rag_index(documents: List[str]) -> tuple:
    """
    Build a RAG index from a list of document texts.
    Returns (vectorstore, embedder, retriever).
    """
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from langchain_community.vectorstores import FAISS
        from langchain_core.documents import Document

        logger.info(f"Building RAG index from {len(documents)} documents")

        # Create document objects with metadata
        doc_objects = [
            Document(page_content=doc, metadata={"source": f"document_{i}"})
            for i, doc in enumerate(documents)
        ]

        # Split documents into chunks
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(doc_objects)
        logger.info(f"Created {len(chunks)} chunks from documents")

        # Create embeddings and vector store
        embedder = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        vectorstore = FAISS.from_documents(chunks, embedder)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

        logger.info("RAG index built successfully")
        return vectorstore, embedder, retriever

    except Exception as e:
        logger.exception(f"Error building RAG index: {e}")
        raise


def query_rag_chain(query: str, retriever, llm):
    """
    Query the RAG chain with context from retrieved documents.
    Returns: (answer, source_docs)
    """
    try:
        from langchain.chains import RetrievalQA
        from langchain.prompts import PromptTemplate

        prompt_template = """You are a legal expert assistant. Answer the question using ONLY the provided context from the legal documents.
        
If the answer is not found in the context, say "The information is not available in the provided documents."

Context:
{context}

Question:
{question}

Answer:"""

        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )

        rag_chain = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": PROMPT}
        )

        result = rag_chain.invoke({"query": query})
        answer = result.get("result") or result.get("answer") or ""
        source_docs = result.get("source_documents", [])

        logger.info(f"RAG query completed: {query[:50]}...")
        return answer, source_docs

    except Exception as e:
        logger.exception(f"Error querying RAG chain: {e}")
        raise

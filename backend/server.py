from fastapi import FastAPI, APIRouter, UploadFile, File, HTTPException, Form
from fastapi.responses import JSONResponse, StreamingResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone
import traceback

# Import custom modules
from .data_loader import extract_text_from_pdf, extract_text_from_docx, extract_text_from_image, clean_text, save_case, load_case, update_case
from .case_processor import CaseProcessor
from .classifier import BaselineClassifier
from .orchestrator import DebateOrchestrator
from .auditor import BiasAuditor
from .auth import auth_router

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Legal Multi-Agent Courtroom Simulator")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize components
case_processor = CaseProcessor()
classifier = BaselineClassifier()
orchestrator = DebateOrchestrator()
auditor = BiasAuditor()


# Define Models
class CaseUploadResponse(BaseModel):
    case_id: str
    raw_text: str
    message: str


class CaseProcessResponse(BaseModel):
    case_id: str
    facts: str
    issues: str
    holding: str


class ClassifierResponse(BaseModel):
    case_id: str
    prediction: str
    confidence: float
    method: str


class SimulationResponse(BaseModel):
    case_id: str
    debate_transcript: List[Dict[str, Any]]
    verdict: Dict[str, Any]
    rounds_completed: int


class AuditResponse(BaseModel):
    case_id: str
    audit_result: Dict[str, Any]


class ChatbotResponse(BaseModel):
    case_id: str
    question: str
    answer: str
    student_friendly: bool = True


class AnnotationRequest(BaseModel):
    text: str
    annotation: str
    note: str = ""


# Routes
@api_router.get("/")
async def root():
    return {"message": "Legal Multi-Agent Courtroom Simulator API"}


@api_router.post("/upload", response_model=CaseUploadResponse)
async def upload_document(files: List[UploadFile] = File(...), jurisdiction: str = Form(default="India")):
    """Upload multiple documents (PDF, Word, images, or text) and extract raw text with OCR support."""
    try:
        if not files or len(files) == 0:
            raise HTTPException(status_code=400, detail="At least one file must be provided")
        
        all_text = []
        filenames = []
        
        for file in files:
            if not file.filename:
                continue
                
            content = await file.read()
            filename_lower = file.filename.lower()
            raw_text = ""
            
            # Extract text based on file type
            if filename_lower.endswith('.pdf'):
                raw_text = extract_text_from_pdf(content)
            elif filename_lower.endswith('.docx') or filename_lower.endswith('.doc'):
                raw_text = extract_text_from_docx(content)
            elif filename_lower.endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.tif')):
                raw_text = extract_text_from_image(content)
            elif filename_lower.endswith('.txt'):
                raw_text = content.decode('utf-8')
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.filename}. Supported formats: PDF, Word (.docx, .doc), Images (.png, .jpg, .jpeg, .gif, .bmp, .webp, .tiff), TXT")
            
            if raw_text.strip():
                all_text.append(raw_text)
                filenames.append(file.filename)
        
        if not all_text:
            raise HTTPException(status_code=400, detail="No text could be extracted from the provided files")
        
        # Combine all texts
        combined_text = "\n\n--- Document Separator ---\n\n".join(all_text)
        combined_text = clean_text(combined_text)
        
        # Save case with all documents
        case_data = {
            'filenames': filenames,
            'raw_text': combined_text,
            'upload_timestamp': datetime.now(timezone.utc).isoformat(),
            'document_count': len(filenames)
        }
        if jurisdiction:
            case_data['jurisdiction'] = jurisdiction
        
        case_id = save_case(case_data)
        
        # Build RAG index for this case
        try:
            from .ocr_rag import build_rag_index
            from langchain_groq import ChatGroq
            
            vectorstore, embedder, retriever = build_rag_index(all_text)
            
            # Store retriever in case data for later use
            update_case(case_id, {
                'rag_index_available': True,
                'document_sources': filenames
            })
            
            # Set RAG for case processor
            llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=os.environ.get("GROQ_API_KEY"))
            case_processor.set_rag_chain(retriever, llm)
            
            # Store retriever in a simple in-memory cache (for this session)
            # In production, you'd persist this differently
            if not hasattr(app, 'case_rag_cache'):
                app.case_rag_cache = {}
            app.case_rag_cache[case_id] = retriever
            
            logger.info(f"RAG index built for case {case_id} with {len(all_text)} documents")
        except Exception as e:
            logger.warning(f"RAG indexing failed for case {case_id}: {e}. Will use Groq only.")
        
        preview_text = combined_text[:1000] + "..." if len(combined_text) > 1000 else combined_text
        
        return CaseUploadResponse(
            case_id=case_id,
            raw_text=preview_text,
            message=f"Successfully uploaded {len(filenames)} document(s)"
        )
    
    except Exception as e:
        logger.exception(f"Error in multi-file upload: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing files: {str(e)}")


@api_router.post("/process-case/{case_id}", response_model=CaseProcessResponse)
async def process_case(case_id: str):
    """Extract facts, issues, and holding from case document."""
    try:
        case_data = load_case(case_id)
        raw_text = case_data.get('raw_text', '')
        
        # Extract case details using LLM
        extracted = await case_processor.extract_case_details(raw_text)
        
        # Normalize issues - convert list or dict to string if needed
        issues = extracted.get('issues', 'Issues could not be extracted')
        if isinstance(issues, (dict, list)):
            if isinstance(issues, dict):
                if 'issuesList' in issues:
                    issues = ', '.join([str(i) for i in issues['issuesList']])
                elif 'issues' in issues:
                    issues = str(issues['issues'])
                else:
                    issues = str(issues)
            elif isinstance(issues, list):
                issues = ', '.join([str(i) for i in issues])
        
        # Normalize facts
        facts = extracted.get('facts', 'Facts could not be extracted')
        if not isinstance(facts, str):
            facts = str(facts)
        
        # Normalize holding
        holding = extracted.get('holding', 'Holding could not be extracted')
        if not isinstance(holding, str):
            holding = str(holding)
        
        normalized_extracted = {
            'facts': facts,
            'issues': issues,
            'holding': holding
        }
        
        # Update case with extracted details
        update_case(case_id, normalized_extracted)
        
        return CaseProcessResponse(
            case_id=case_id,
            facts=facts,
            issues=issues,
            holding=holding
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing case: {str(e)}")


@api_router.get("/related-laws/{case_id}")
async def related_laws(case_id: str, jurisdiction: Optional[str] = None):
    """Find related laws for a case and jurisdiction using the CaseProcessor LLM helper."""
    try:
        case_data = load_case(case_id)
        raw_text = case_data.get('raw_text', '')

        # If jurisdiction not provided in query, use stored case jurisdiction or default to India
        jur = jurisdiction or case_data.get('jurisdiction', 'India')

        laws_result = await case_processor.find_related_laws(raw_text, jur)

        # Update the case record with the found laws
        update_case(case_id, {'jurisdiction': jur, 'related_laws': laws_result.get('laws', [])})

        return JSONResponse(content={'case_id': case_id, 'jurisdiction': jur, 'laws': laws_result.get('laws', [])})

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error finding related laws: {str(e)}")


@api_router.post("/predict/{case_id}", response_model=ClassifierResponse)
async def predict_outcome(case_id: str):
    """Predict case outcome using baseline classifier."""
    try:
        case_data = load_case(case_id)
        
        # Run baseline classifier
        prediction = classifier.predict(case_data)
        
        # Update case with prediction
        update_case(case_id, {'baseline_prediction': prediction})
        
        return ClassifierResponse(
            case_id=case_id,
            prediction=prediction['prediction'],
            confidence=prediction['confidence'],
            method=prediction['method']
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error predicting outcome: {str(e)}")


@api_router.post("/simulate/{case_id}", response_model=SimulationResponse)
async def run_simulation(case_id: str, rounds: int = 4):
    """Run multi-agent debate simulation with dynamic rounds based on debate progression.
    
    Args:
        case_id: The case ID to simulate
        rounds: Maximum number of debate rounds (default 4, minimum 3 will run)
    """
    try:
        case_data = load_case(case_id)
        
        # Ensure case has been processed
        if 'facts' not in case_data:
            raise HTTPException(status_code=400, detail="Case must be processed before simulation")
        
        # Run simulation with dynamic rounds (min 3, max based on rounds param)
        min_rounds = min(3, rounds)
        max_rounds = max(3, rounds)
        simulation_result = await orchestrator.run_simulation(case_data, max_rounds=max_rounds, min_rounds=min_rounds)
        
        # Update case with simulation results
        update_case(case_id, {'simulation': simulation_result})
        
        return SimulationResponse(
            case_id=case_id,
            debate_transcript=simulation_result['debate_transcript'],
            verdict=simulation_result['verdict'],
            rounds_completed=simulation_result['rounds_completed']
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running simulation: {str(e)}")


@api_router.post("/audit/{case_id}", response_model=AuditResponse)
async def audit_case(case_id: str):
    """Perform bias audit on case and verdict."""
    try:
        case_data = load_case(case_id)
        
        # Ensure simulation has been run
        if 'simulation' not in case_data:
            raise HTTPException(status_code=400, detail="Simulation must be run before audit")
        
        verdict = case_data['simulation']['verdict']
        
        # Run audit
        audit_result = await auditor.audit(case_data, verdict)
        
        # Update case with audit results
        update_case(case_id, {'audit': audit_result})
        
        return AuditResponse(
            case_id=case_id,
            audit_result=audit_result
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error auditing case: {str(e)}")


@api_router.post("/chatbot/{case_id}", response_model=ChatbotResponse)
async def chatbot_answer(case_id: str, question: str = Form(...)):
    """Answer questions about the current case - student-friendly explanations."""
    try:
        case_data = load_case(case_id)
        
        # Prepare context from case data - use available information
        # Check for processed case details (facts, issues, holding)
        if 'facts' in case_data:
            facts = case_data.get('facts', '')
        elif 'case_details' in case_data:
            facts = case_data['case_details'].get('facts', '')
        else:
            facts = case_data.get('raw_text', '')[:2000]
        
        # Get prediction if available
        prediction = case_data.get('baseline_prediction', {})
        if isinstance(prediction, dict):
            prediction_text = prediction.get('prediction', 'Not yet available')
        else:
            prediction_text = 'Not yet available'
        
        # Get simulation/verdict if available
        simulation = case_data.get('simulation', {})
        verdict_obj = simulation.get('verdict', {}) if simulation else {}
        
        # Format verdict text based on new verdict structure
        if isinstance(verdict_obj, dict):
            verdict_type = verdict_obj.get('verdict', 'Pending')
            ruling = verdict_obj.get('ruling', '')
            remedy = verdict_obj.get('remedy', '')
            penalty_info = verdict_obj.get('penalty_info', {})
            
            if ruling and remedy:
                verdict_text = f"{ruling}\n{remedy}"
            elif remedy:
                verdict_text = remedy
            elif penalty_info.get('description'):
                verdict_text = f"Verdict: {verdict_type}\nRemedy: {penalty_info.get('description')}"
            else:
                verdict_text = f"Court Verdict: {verdict_type}"
        else:
            verdict_text = 'Court decision pending'
        
        # Use available information for context
        if not facts or len(str(facts)) < 50:
            facts = case_data.get('raw_text', 'Case details being processed')[:2000]
        
        # Build prompt for student-friendly answer
        prompt = f"""You are an expert legal tutor helping a law student understand a court case. 
        
Student's question: {question}

Case Facts (summary): {facts[:1500]}
Predicted Outcome: {prediction_text}
Court Verdict: {verdict_text}

Guidelines for your response:
1. Use simple, clear language avoiding legal jargon where possible
2. Explain any legal terms you must use
3. Relate the answer to the case facts and verdict
4. Help the student understand the reasoning
5. Keep the answer concise (2-3 paragraphs max)
6. Be encouraging and educational

Provide a clear, student-friendly answer:"""
        
        try:
            from langchain_groq import ChatGroq
            
            llm = ChatGroq(model="llama-3.3-70b-versatile", groq_api_key=os.environ.get("GROQ_API_KEY"))
            response = llm.invoke(prompt)
            answer = response.content if hasattr(response, 'content') else str(response)
            
        except Exception as llm_error:
            logger.warning(f"Groq API error for chatbot: {llm_error}. Using fallback response.")
            # Fallback response if Groq fails
            answer = f"Based on the case analysis: The predicted outcome was {prediction_text}. The court's verdict was {verdict_text}. To better answer your question about '{question}', please review the case facts and the debate transcript."
        
        return ChatbotResponse(
            case_id=case_id,
            question=question,
            answer=answer,
            student_friendly=True
        )
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        logger.error(f"Chatbot error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error answering question: {str(e)}")


@api_router.get("/case/{case_id}")
async def get_case(case_id: str):
    """Get complete case details."""
    try:
        case_data = load_case(case_id)
        return JSONResponse(content=case_data)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving case: {str(e)}")


@api_router.get("/case-pdf/{case_id}")
async def case_pdf(case_id: str):
    """Generate a simple PDF report for the case including verdict, evidence and evaluation metrics."""
    try:
        case_data = load_case(case_id)

        # Ensure simulation result exists before generating PDF
        if 'simulation' not in case_data:
            raise HTTPException(status_code=400, detail="Simulation must be run before generating PDF")

        # Create PDF in-memory
        from io import BytesIO
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
        except Exception as e:
            raise RuntimeError("reportlab not available; please install reportlab in the backend environment")

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 50

        c.setFont("Helvetica-Bold", 14)
        c.drawString(50, y, f"Case Report: {case_id}")
        y -= 30

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Verdict:")
        y -= 18
        c.setFont("Helvetica", 10)
        verdict = case_data.get('simulation', {}).get('verdict', {})
        c.drawString(60, y, verdict.get('verdict', 'N/A'))
        y -= 15
        c.drawString(60, y, f"Confidence: {verdict.get('confidence', 'N/A')}")
        y -= 20

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Supporting Evidence:")
        y -= 18
        c.setFont("Helvetica", 10)
        for ev in verdict.get('supporting_evidence', []):
            for line in ev.split('\n'):
                c.drawString(60, y, f"- {line}")
                y -= 12
                if y < 80:
                    c.showPage()
                    y = height - 50

        c.setFont("Helvetica-Bold", 12)
        if case_data.get('audit'):
            c.drawString(50, y, "Audit / Evaluation Metrics:")
            y -= 18
            c.setFont("Helvetica", 10)
            audit = case_data.get('audit', {})
            c.drawString(60, y, f"Fairness score: {audit.get('fairness_score', 'N/A')}")
            y -= 12
            c.drawString(60, y, f"Bias types: {', '.join(audit.get('bias_types', []))}")
            y -= 15
        else:
            c.drawString(50, y, "Audit / Evaluation Metrics: None")
            y -= 18

        c.setFont("Helvetica-Bold", 12)
        c.drawString(50, y, "Related Laws:")
        y -= 18
        c.setFont("Helvetica", 10)
        for law in case_data.get('related_laws', []):
            citation = law.get('citation') or ''
            summary = law.get('summary') or ''
            text = f"{citation} - {summary}" if citation else summary
            for line in (text or '').split('\n'):
                c.drawString(60, y, line[:90])
                y -= 12
                if y < 80:
                    c.showPage()
                    y = height - 50

        c.showPage()
        c.save()
        buffer.seek(0)

        headers = {"Content-Disposition": f"attachment; filename=case_{case_id}.pdf"}
        return StreamingResponse(buffer, media_type="application/pdf", headers=headers)

    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        # Log full traceback to server logs and return structured JSON error so frontend can show it
        logger = logging.getLogger(__name__)
        logger.exception("Error generating PDF for case %s", case_id)
        tb = traceback.format_exc()
        # Return JSON with detail and a short trace (first 1024 chars)
        return JSONResponse(content={"detail": f"Error generating PDF: {str(e)}", "trace": tb[:1024]}, status_code=500)


@api_router.get("/reportlab-check")
async def reportlab_check():
    """Internal diagnostic endpoint: reports whether reportlab is importable."""
    try:
        import reportlab
        return JSONResponse(content={"installed": True, "version": getattr(reportlab, '__version__', 'unknown')})
    except Exception as e:
        return JSONResponse(content={"installed": False, "error": str(e)})


@api_router.get("/local-model-check")
async def local_model_check():
    """Diagnostic endpoint: reports whether the local model (qwenn_model) was successfully loaded by agents."""
    try:
        # Import agents module and inspect loader variables
        from . import agents as agents_module

        loaded = getattr(agents_module, '_local_model', None) is not None and getattr(agents_module, '_local_tokenizer', None) is not None
        return JSONResponse(content={"local_model_loaded": bool(loaded)})
    except Exception as e:
        return JSONResponse(content={"local_model_loaded": False, "error": str(e)})


# ============ DASHBOARD & CASE HISTORY ENDPOINTS ============

@api_router.get("/cases")
async def get_all_cases():
    """Get all cases with dashboard statistics."""
    try:
        cases_dir = ROOT_DIR / 'cases'
        if not cases_dir.exists():
            return JSONResponse(content={
                "cases": [],
                "stats": {
                    "total_cases": 0,
                    "avg_confidence": 0,
                    "jurisdiction_breakdown": {}
                }
            })
        
        cases = []
        jurisdictions = {}
        total_confidence = 0
        confidence_count = 0
        
        for case_file in cases_dir.glob('*.json'):
            try:
                case_data = load_case(case_file.stem)
                
                # Extract key metadata
                case_summary = {
                    'case_id': case_file.stem,
                    'jurisdiction': case_data.get('jurisdiction', 'Unknown'),
                    'upload_timestamp': case_data.get('upload_timestamp', ''),
                    'filenames': case_data.get('filenames', []),
                    'facts': case_data.get('facts', '')[:200],  # Preview
                    'issues': case_data.get('issues', '')[:200],
                    'holding': case_data.get('holding', '')[:200],
                    'has_prediction': 'prediction' in case_data,
                    'has_simulation': 'simulation' in case_data,
                    'has_audit': 'audit_result' in case_data
                }
                
                if 'prediction' in case_data:
                    conf = case_data.get('prediction', {}).get('confidence', 0)
                    if isinstance(conf, (int, float)):
                        total_confidence += conf
                        confidence_count += 1
                    case_summary['prediction_confidence'] = conf
                
                # Track jurisdiction
                jur = case_data.get('jurisdiction', 'Unknown')
                jurisdictions[jur] = jurisdictions.get(jur, 0) + 1
                
                cases.append(case_summary)
            except Exception as e:
                logger.warning(f"Could not load case {case_file.stem}: {e}")
                continue
        
        # Calculate stats
        avg_confidence = (total_confidence / confidence_count * 100) if confidence_count > 0 else 0
        
        stats = {
            'total_cases': len(cases),
            'avg_confidence': round(avg_confidence, 2),
            'jurisdiction_breakdown': jurisdictions,
            'cases_with_prediction': sum(1 for c in cases if c.get('has_prediction')),
            'cases_with_simulation': sum(1 for c in cases if c.get('has_simulation')),
            'cases_with_audit': sum(1 for c in cases if c.get('has_audit'))
        }
        
        return JSONResponse(content={
            "cases": cases,
            "stats": stats
        })
    
    except Exception as e:
        logger.exception(f"Error fetching cases: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching cases: {str(e)}")


@api_router.get("/cases/search")
async def search_cases(q: str = "", jurisdiction: Optional[str] = None, has_simulation: bool = False):
    """Search and filter cases by query, jurisdiction, or status."""
    try:
        cases_dir = ROOT_DIR / 'cases'
        if not cases_dir.exists():
            return JSONResponse(content={"cases": [], "count": 0})
        
        results = []
        q_lower = q.lower()
        
        for case_file in cases_dir.glob('*.json'):
            try:
                case_data = load_case(case_file.stem)
                
                # Filter by jurisdiction
                if jurisdiction and case_data.get('jurisdiction', 'Unknown') != jurisdiction:
                    continue
                
                # Filter by simulation status
                if has_simulation and 'simulation' not in case_data:
                    continue
                
                # Filter by search query
                if q:
                    search_fields = [
                        case_data.get('facts', ''),
                        case_data.get('issues', ''),
                        case_data.get('holding', ''),
                        ' '.join(case_data.get('filenames', []))
                    ]
                    if not any(q_lower in field.lower() for field in search_fields):
                        continue
                
                case_summary = {
                    'case_id': case_file.stem,
                    'jurisdiction': case_data.get('jurisdiction', 'Unknown'),
                    'upload_timestamp': case_data.get('upload_timestamp', ''),
                    'facts': case_data.get('facts', '')[:150],
                    'issues': case_data.get('issues', '')[:150]
                }
                results.append(case_summary)
            except Exception as e:
                logger.warning(f"Error searching case {case_file.stem}: {e}")
                continue
        
        return JSONResponse(content={"cases": results, "count": len(results)})
    
    except Exception as e:
        logger.exception(f"Error searching cases: {e}")
        raise HTTPException(status_code=500, detail=f"Error searching cases: {str(e)}")


@api_router.post("/case-comparison")
async def compare_cases(case_ids: List[str]):
    """Compare 2-3 cases side-by-side."""
    try:
        if len(case_ids) < 2 or len(case_ids) > 3:
            raise HTTPException(status_code=400, detail="Please provide 2-3 case IDs for comparison")
        
        comparison = {
            'case_ids': case_ids,
            'cases': [],
            'similarities': [],
            'differences': []
        }
        
        cases_data = []
        for case_id in case_ids:
            try:
                case_data = load_case(case_id)
                cases_data.append({
                    'case_id': case_id,
                    'facts': case_data.get('facts', ''),
                    'issues': case_data.get('issues', ''),
                    'holding': case_data.get('holding', ''),
                    'jurisdiction': case_data.get('jurisdiction', 'Unknown'),
                    'prediction': case_data.get('prediction', {})
                })
            except FileNotFoundError:
                raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
        
        comparison['cases'] = cases_data
        
        # Find similarities and differences
        if len(cases_data) >= 2:
            # Simple similarity detection based on keywords
            all_keywords = set()
            for case in cases_data:
                keywords = set((case.get('issues', '') + ' ' + case.get('holding', '')).lower().split())
                all_keywords.update(keywords)
            
            # Find common keywords
            common_keywords = set.intersection(*[
                set((case.get('issues', '') + ' ' + case.get('holding', '')).lower().split())
                for case in cases_data
            ])
            
            if common_keywords:
                comparison['similarities'] = list(common_keywords)[:5]
            
            # Find differences by checking unique aspects
            for i, case in enumerate(cases_data):
                unique_aspects = set(case.get('issues', '').lower().split()) - common_keywords
                if unique_aspects:
                    comparison['differences'].append({
                        'case_index': i,
                        'aspects': list(unique_aspects)[:3]
                    })
        
        return JSONResponse(content=comparison)
    
    except Exception as e:
        logger.exception(f"Error comparing cases: {e}")
        raise HTTPException(status_code=500, detail=f"Error comparing cases: {str(e)}")


@api_router.post("/case/{case_id}/annotations")
async def add_annotation(case_id: str, annotation_request: AnnotationRequest):
    """Add an annotation to a case."""
    try:
        case_data = load_case(case_id)
        
        if 'annotations' not in case_data:
            case_data['annotations'] = []
        
        annotation_entry = {
            'text': annotation_request.text,
            'annotation': annotation_request.annotation,
            'note': annotation_request.note,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        case_data['annotations'].append(annotation_entry)
        update_case(case_id, {'annotations': case_data['annotations']})
        
        return JSONResponse(content={
            'case_id': case_id,
            'annotation': annotation_entry,
            'message': 'Annotation added successfully'
        })
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        logger.exception(f"Error adding annotation: {e}")
        raise HTTPException(status_code=500, detail=f"Error adding annotation: {str(e)}")


@api_router.get("/case/{case_id}/annotations")
async def get_annotations(case_id: str):
    """Get all annotations for a case."""
    try:
        case_data = load_case(case_id)
        annotations = case_data.get('annotations', [])
        
        return JSONResponse(content={
            'case_id': case_id,
            'annotations': annotations,
            'count': len(annotations)
        })
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        logger.exception(f"Error fetching annotations: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching annotations: {str(e)}")


@api_router.get("/case/{case_id}/summary")
async def get_case_summary(case_id: str):
    """Get comprehensive case summary with all metadata."""
    try:
        case_data = load_case(case_id)
        
        summary = {
            'case_id': case_id,
            'jurisdiction': case_data.get('jurisdiction', 'Unknown'),
            'upload_timestamp': case_data.get('upload_timestamp', ''),
            'filenames': case_data.get('filenames', []),
            'facts': case_data.get('facts', ''),
            'issues': case_data.get('issues', ''),
            'holding': case_data.get('holding', ''),
            'prediction': case_data.get('prediction', None),
            'simulation': case_data.get('simulation', None),
            'audit': case_data.get('audit_result', None),
            'related_laws': case_data.get('related_laws', []),
            'annotations': case_data.get('annotations', []),
            'annotations_count': len(case_data.get('annotations', []))
        }
        
        return JSONResponse(content=summary)
    
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Case not found")
    except Exception as e:
        logger.exception(f"Error fetching case summary: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching case summary: {str(e)}")


# Include the router in the main app
app.include_router(api_router)
app.include_router(auth_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

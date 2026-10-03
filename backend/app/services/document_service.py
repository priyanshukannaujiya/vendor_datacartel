import os
import re
import csv
import logging
from typing import Dict, Any, Optional, Tuple, List
from io import BytesIO

from app.schemas.document import (
    DocumentType,
    DocumentExtractionStatus,
    COAExtractionData,
    SDSExtractionData,
    GMPExtractionData,
    GenericExtractionData,
    DocumentProcessResult,
)

logger = logging.getLogger(__name__)


class DocumentProcessingService:
    """
    Developer 2 Document Processing Service.
    Extracts text and structured key-value pairs from PDF, CSV, XLSX, and DOCX files.
    Identifies fields for COA, SDS, GMP, SPECIFICATION, TEST_REPORT, COMPLIANCE.
    
    CRITICAL SAFETY RULES:
    1. NEVER hallucinate or fabricate values.
    2. If information cannot be extracted, flag as MISSING or mark status as NEEDS_REVIEW.
    3. Gracefully handle malformed, corrupted, or empty files.
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".csv", ".xlsx", ".docx", ".txt"}

    def __init__(self):
        pass

    def extract_raw_text(self, file_path_or_bytes: Any, filename: str) -> str:
        """
        Reads raw text from PDF, CSV, XLSX, DOCX, or TXT.
        Accepts either a filesystem path or raw bytes/BytesIO.
        """
        ext = os.path.splitext(filename)[1].lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file format '{ext}'. Supported: {list(self.SUPPORTED_EXTENSIONS)}")

        # Convert to file-like object or path
        is_path = isinstance(file_path_or_bytes, str) and os.path.exists(file_path_or_bytes)
        
        if ext == ".txt":
            if is_path:
                with open(file_path_or_bytes, "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            else:
                data = file_path_or_bytes if isinstance(file_path_or_bytes, bytes) else file_path_or_bytes.read()
                return data.decode("utf-8", errors="replace")

        elif ext == ".pdf":
            return self._extract_pdf_text(file_path_or_bytes, is_path)

        elif ext == ".csv":
            return self._extract_csv_text(file_path_or_bytes, is_path)

        elif ext == ".xlsx":
            return self._extract_xlsx_text(file_path_or_bytes, is_path)

        elif ext == ".docx":
            return self._extract_docx_text(file_path_or_bytes, is_path)

        return ""

    def _extract_pdf_text(self, file_source: Any, is_path: bool) -> str:
        try:
            import pypdf
            reader = pypdf.PdfReader(file_source if is_path else (
                BytesIO(file_source) if isinstance(file_source, bytes) else file_source
            ))
            text_parts = []
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return "\n".join(text_parts)
        except Exception as e:
            logger.error(f"Error extracting PDF: {str(e)}")
            raise RuntimeError(f"Corrupted or invalid PDF file: {str(e)}")

    def _extract_csv_text(self, file_source: Any, is_path: bool) -> str:
        try:
            lines = []
            if is_path:
                with open(file_source, "r", encoding="utf-8", errors="replace") as f:
                    reader = csv.reader(f)
                    for row in reader:
                        lines.append(" | ".join(row))
            else:
                content = file_source if isinstance(file_source, bytes) else file_source.read()
                text_stream = content.decode("utf-8", errors="replace").splitlines()
                reader = csv.reader(text_stream)
                for row in reader:
                    lines.append(" | ".join(row))
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"Error extracting CSV: {str(e)}")
            raise RuntimeError(f"Corrupted or invalid CSV file: {str(e)}")

    def _extract_xlsx_text(self, file_source: Any, is_path: bool) -> str:
        try:
            import openpyxl
            wb = openpyxl.load_workbook(
                file_source if is_path else (BytesIO(file_source) if isinstance(file_source, bytes) else file_source),
                data_only=True
            )
            text_lines = []
            for sheetname in wb.sheetnames:
                sheet = wb[sheetname]
                text_lines.append(f"--- Sheet: {sheetname} ---")
                for row in sheet.iter_rows(values_only=True):
                    row_vals = [str(v) if v is not None else "" for v in row]
                    if any(row_vals):
                        text_lines.append(" | ".join(row_vals))
            return "\n".join(text_lines)
        except Exception as e:
            logger.error(f"Error extracting XLSX: {str(e)}")
            raise RuntimeError(f"Corrupted or invalid Excel file: {str(e)}")

    def _extract_docx_text(self, file_source: Any, is_path: bool) -> str:
        try:
            import docx
            doc = docx.Document(
                file_source if is_path else (BytesIO(file_source) if isinstance(file_source, bytes) else file_source)
            )
            paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells]
                    paragraphs.append(" | ".join(row_text))
            return "\n".join(paragraphs)
        except Exception as e:
            logger.error(f"Error extracting DOCX: {str(e)}")
            raise RuntimeError(f"Corrupted or invalid DOCX file: {str(e)}")

    # -------------------------------------------------------------
    # COA Extraction
    # -------------------------------------------------------------
    def extract_coa(self, raw_text: str) -> Tuple[COAExtractionData, List[str]]:
        """
        Extracts key laboratory parameters from COA text:
        - batch_number
        - material
        - purity (assay)
        - moisture (water content)
        - heavy_metals
        - microbial_parameters
        - test_date
        - manufacturing_date
        - expiry_date
        - laboratory
        """
        missing_fields: List[str] = []
        notes: List[str] = []

        batch_number = None
        purity = None
        moisture = None
        material = None

        # Line-by-line tabular parsing pass
        lines = [line.strip() for line in raw_text.splitlines() if line.strip()]
        for line in lines:
            if "|" in line:
                cells = [c.strip() for c in line.split("|") if c.strip()]
                if len(cells) >= 2:
                    header = cells[0].lower()
                    last_val = cells[-1]
                    
                    if "batch" in header or "lot" in header:
                        cand = re.sub(r"[^A-Za-z0-9\-_/]", "", last_val)
                        if cand and not batch_number:
                            batch_number = cand

                    if "purity" in header or "assay" in header:
                        m_num = re.search(r"(\d+(?:\.\d+)?)", last_val)
                        if m_num and purity is None:
                            val = float(m_num.group(1))
                            if 0.0 <= val <= 100.0:
                                purity = val

                    if "moisture" in header or "water" in header or "lod" in header:
                        m_num = re.search(r"(\d+(?:\.\d+)?)", last_val)
                        if m_num and moisture is None:
                            moisture = float(m_num.group(1))

        # 1. Batch Number
        if not batch_number:
            batch_patterns = [
                r"(?:Batch\s*(?:No|Number|#)|Lot\s*(?:No|Number|#)|Lot)\s*[:=\-]?\s*([A-Za-z0-9\-_/]+)",
                r"(?:Batch\s*ID)\s*[:=\-]?\s*([A-Za-z0-9\-_/]+)",
            ]
            for pat in batch_patterns:
                m = re.search(pat, raw_text, re.IGNORECASE)
                if m:
                    batch_number = m.group(1).strip()
                    break
        if not batch_number:
            missing_fields.append("batch_number")

        # 2. Material / Product Name
        material = None
        material_patterns = [
            r"(?:Material|Product\s*Name|Item\s*Name|Substance|Sample\s*Name)\s*[:=\-]?\s*([^\n\r,|;]+)",
            r"(?:Product)\s*[:=\-]?\s*([^\n\r,|;]+)",
        ]
        for pat in material_patterns:
            m = re.search(pat, raw_text, re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                if cand.lower() not in {"coa", "certificate of analysis", "specification"}:
                    material = cand
                    break
        if not material:
            missing_fields.append("material")

        # 3. Purity / Assay
        if purity is None:
            purity_patterns = [
                r"(?:Purity|Assay|Content)(?:\s*\([^)]*\))?\s*[:=\-|]?\s*(?:[\w\s<>]+[:=\-|])?\s*(\d+(?:\.\d+)?)\s*%",
                r"(?:Purity|Assay|Content)(?:\s*\([^)]*\))?\s*[:=\-|]?\s*(\d+(?:\.\d+)?)",
            ]
            for pat in purity_patterns:
                m = re.search(pat, raw_text, re.IGNORECASE)
                if m:
                    val = float(m.group(1))
                    if 0.0 <= val <= 100.0:
                        purity = val
                        break
        if purity is None:
            missing_fields.append("purity")

        # 4. Moisture / Water Content / Loss on Drying (LOD)
        if moisture is None:
            moisture_patterns = [
                r"(?:Moisture|Water\s*Content|Loss\s*on\s*Drying|LOD)(?:\s*\([^)]*\))?\s*[:=\-|]?\s*(?:[\w\s<>]+[:=\-|])?\s*(\d+(?:\.\d+)?)\s*%",
                r"(?:Moisture|Water\s*Content|LOD)(?:\s*\([^)]*\))?\s*[:=\-|]?\s*(\d+(?:\.\d+)?)",
            ]
            for pat in moisture_patterns:
                m = re.search(pat, raw_text, re.IGNORECASE)
                if m:
                    moisture = float(m.group(1))
                    break
        if moisture is None:
            missing_fields.append("moisture")

        # 5. Heavy Metals
        heavy_metals = None
        hm_match = re.search(
            r"(?:Heavy\s*Metals|Lead\s*\(Pb\)|Total\s*Heavy\s*Metals)(?:\s*\([^)]*\))?\s*[:=\-|]?\s*(?:<\s*)?(\d+(?:\.\d+)?)\s*(?:ppm|mg/kg|%)?",
            raw_text,
            re.IGNORECASE
        )
        if hm_match:
            heavy_metals = float(hm_match.group(1))
        else:
            if re.search(r"Heavy\s*Metals\s*[:=\-|]?\s*(?:Not\s*Detected|ND|Conforms|<LOQ)", raw_text, re.IGNORECASE):
                heavy_metals = 0.0
                notes.append("Heavy metals reported as Not Detected/Conforms (recorded as 0.0 ppm)")
            else:
                missing_fields.append("heavy_metals")

        # 6. Microbial Parameters
        microbial_params = {}
        tamc_match = re.search(r"(?:TAMC|Total\s*Aerobic\s*Microbial\s*Count)(?:\s*\([^)]*\))?\s*[:=\-|]?\s*(?:<\s*)?(\d+(?:\.\d+)?)", raw_text, re.IGNORECASE)
        if tamc_match:
            microbial_params["TAMC_cfu_g"] = float(tamc_match.group(1))
        tymc_match = re.search(r"(?:TYMC|Total\s*Yeast\s*and\s*Mold|Yeast\s*and\s*Mold)(?:\s*\([^)]*\))?\s*[:=\-|]?\s*(?:<\s*)?(\d+(?:\.\d+)?)", raw_text, re.IGNORECASE)
        if tymc_match:
            microbial_params["TYMC_cfu_g"] = float(tymc_match.group(1))
        ecoli_match = re.search(r"(?:E\.?\s*coli|Escherichia\s*coli)\s*[:=\-|]?\s*(Absent|Negative|Conforms|Detected)", raw_text, re.IGNORECASE)
        if ecoli_match:
            microbial_params["E_coli"] = ecoli_match.group(1)
        if not microbial_params:
            missing_fields.append("microbial_parameters")

        # 7. Dates (Test Date, Manufacturing Date, Expiry Date)
        date_pattern = r"(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})"
        
        test_date = None
        m_td = re.search(rf"(?:Test\s*Date|Analysis\s*Date|Date\s*of\s*Testing)\s*[:=\-]?\s*{date_pattern}", raw_text, re.IGNORECASE)
        if m_td:
            test_date = m_td.group(1)
        else:
            missing_fields.append("test_date")

        mfg_date = None
        m_mfg = re.search(rf"(?:Mfg\s*Date|Manufacturing\s*Date|Production\s*Date|Date\s*of\s*Manufacture)\s*[:=\-]?\s*{date_pattern}", raw_text, re.IGNORECASE)
        if m_mfg:
            mfg_date = m_mfg.group(1)
        else:
            missing_fields.append("manufacturing_date")

        exp_date = None
        m_exp = re.search(rf"(?:Expiry\s*Date|Expiration\s*Date|Exp\s*Date|Best\s*Before|Retest\s*Date)\s*[:=\-]?\s*{date_pattern}", raw_text, re.IGNORECASE)
        if m_exp:
            exp_date = m_exp.group(1)
        else:
            missing_fields.append("expiry_date")

        # 8. Laboratory
        laboratory = None
        lab_match = re.search(r"(?:Laboratory|Testing\s*Facility|Analyst\s*Lab|Quality\s*Control\s*Lab|Issued\s*By)\s*[:=\-]?\s*([^\n\r,|;]+)", raw_text, re.IGNORECASE)
        if lab_match:
            laboratory = lab_match.group(1).strip()
        else:
            missing_fields.append("laboratory")

        data = COAExtractionData(
            batch_number=batch_number,
            material=material,
            purity=purity,
            moisture=moisture,
            heavy_metals=heavy_metals,
            microbial_parameters=microbial_params if microbial_params else None,
            test_date=test_date,
            manufacturing_date=mfg_date,
            expiry_date=exp_date,
            laboratory=laboratory,
            extraction_notes=notes,
        )

        return data, missing_fields

    # -------------------------------------------------------------
    # SDS Extraction
    # -------------------------------------------------------------
    def extract_sds(self, raw_text: str) -> Tuple[SDSExtractionData, List[str]]:
        missing_fields: List[str] = []
        notes: List[str] = []

        product_name = None
        m_prod = re.search(r"(?:Product\s*Name|Identification|Trade\s*Name)\s*[:=\-]?\s*([^\n\r,|;]+)", raw_text, re.IGNORECASE)
        if m_prod:
            product_name = m_prod.group(1).strip()
        else:
            missing_fields.append("product_name")

        cas_number = None
        m_cas = re.search(r"(?:CAS\s*(?:No|Number|#)?)\s*[:=\-]?\s*(\d{2,7}-\d{2}-\d)", raw_text, re.IGNORECASE)
        if m_cas:
            cas_number = m_cas.group(1).strip()
        else:
            missing_fields.append("cas_number")

        hazard_statements = []
        for hz in re.findall(r"(H\d{3}[a-zA-Z]?\s*[:\-]?\s*[^\n\r;]+)", raw_text):
            hazard_statements.append(hz.strip())

        storage_requirements = None
        m_store = re.search(r"(?:Storage(?:\s*Conditions)?|Handling\s*and\s*Storage)\s*[:=\-]?\s*([^\n\r;]+)", raw_text, re.IGNORECASE)
        if m_store:
            storage_requirements = m_store.group(1).strip()
        else:
            missing_fields.append("storage_requirements")

        rev_date = None
        m_rev = re.search(r"(?:Revision\s*Date|Version\s*Date|Date\s*of\s*Issue)\s*[:=\-]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", raw_text, re.IGNORECASE)
        if m_rev:
            rev_date = m_rev.group(1).strip()

        data = SDSExtractionData(
            product_name=product_name,
            cas_number=cas_number,
            hazard_statements=hazard_statements,
            storage_requirements=storage_requirements,
            revision_date=rev_date,
            extraction_notes=notes,
        )
        return data, missing_fields

    # -------------------------------------------------------------
    # GMP Extraction
    # -------------------------------------------------------------
    def extract_gmp(self, raw_text: str) -> Tuple[GMPExtractionData, List[str]]:
        missing_fields: List[str] = []
        notes: List[str] = []

        cert_num = None
        m_cert = re.search(r"(?:Certificate\s*(?:No|Number|#)|GMP\s*Cert\s*#)\s*[:=\-]?\s*([A-Za-z0-9\-_/]+)", raw_text, re.IGNORECASE)
        if m_cert:
            cert_num = m_cert.group(1).strip()
        else:
            missing_fields.append("certificate_number")

        issuing_body = None
        m_body = re.search(r"(?:Issuing\s*Authority|Authority|Certifying\s*Body|Auditor)\s*[:=\-]?\s*([^\n\r,|;]+)", raw_text, re.IGNORECASE)
        if m_body:
            issuing_body = m_body.group(1).strip()
        else:
            missing_fields.append("issuing_body")

        valid_until = None
        m_val = re.search(r"(?:Valid\s*(?:Until|Through|To)|Expiry\s*Date|Expires)\s*[:=\-]?\s*(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})", raw_text, re.IGNORECASE)
        if m_val:
            valid_until = m_val.group(1).strip()
        else:
            missing_fields.append("valid_until")

        is_valid = True if valid_until else None

        scope = None
        m_scope = re.search(r"(?:Scope\s*of\s*(?:Certification|Activity)|Scope)\s*[:=\-]?\s*([^\n\r;]+)", raw_text, re.IGNORECASE)
        if m_scope:
            scope = m_scope.group(1).strip()

        data = GMPExtractionData(
            certificate_number=cert_num,
            issuing_body=issuing_body,
            valid_until=valid_until,
            is_valid=is_valid,
            scope=scope,
            extraction_notes=notes,
        )
        return data, missing_fields

    # -------------------------------------------------------------
    # Generic Processor
    # -------------------------------------------------------------
    def extract_generic(self, raw_text: str) -> Tuple[GenericExtractionData, List[str]]:
        summary_lines = [line.strip() for line in raw_text.splitlines() if line.strip()][:5]
        summary = " ".join(summary_lines) if summary_lines else None
        return GenericExtractionData(
            title="Document Processed",
            summary=summary,
            parameters={"line_count": len(raw_text.splitlines())}
        ), []

    # -------------------------------------------------------------
    # Main Process Entrypoint
    # -------------------------------------------------------------
    def process_document(
        self,
        file_source: Any,
        filename: str,
        document_type: DocumentType,
        document_id: Optional[int] = None
    ) -> DocumentProcessResult:
        """
        Processes a single document file or bytes, extracts parameters according
        to document type, and returns a structured DocumentProcessResult.
        """
        try:
            raw_text = self.extract_raw_text(file_source, filename)
            if not raw_text or not raw_text.strip():
                return DocumentProcessResult(
                    document_id=document_id,
                    filename=filename,
                    document_type=document_type,
                    status=DocumentExtractionStatus.NEEDS_REVIEW,
                    extracted_data={},
                    missing_fields=["content"],
                    error="Document is empty or unreadable text."
                )

            extracted_data_dict: Dict[str, Any] = {}
            missing_fields: List[str] = []

            if document_type == DocumentType.COA:
                coa_data, missing_fields = self.extract_coa(raw_text)
                extracted_data_dict = coa_data.model_dump()
            elif document_type == DocumentType.SDS:
                sds_data, missing_fields = self.extract_sds(raw_text)
                extracted_data_dict = sds_data.model_dump()
            elif document_type == DocumentType.GMP:
                gmp_data, missing_fields = self.extract_gmp(raw_text)
                extracted_data_dict = gmp_data.model_dump()
            else:
                gen_data, missing_fields = self.extract_generic(raw_text)
                extracted_data_dict = gen_data.model_dump()

            # Rule: If critical information is missing, mark as NEEDS_REVIEW
            # For COA: purity or batch_number missing -> NEEDS_REVIEW
            # For GMP: valid_until or certificate_number missing -> NEEDS_REVIEW
            if document_type == DocumentType.COA and ("purity" in missing_fields or "batch_number" in missing_fields):
                status = DocumentExtractionStatus.NEEDS_REVIEW
            elif document_type == DocumentType.GMP and ("valid_until" in missing_fields or "certificate_number" in missing_fields):
                status = DocumentExtractionStatus.NEEDS_REVIEW
            elif len(missing_fields) > 4:
                status = DocumentExtractionStatus.NEEDS_REVIEW
            else:
                status = DocumentExtractionStatus.PROCESSED

            return DocumentProcessResult(
                document_id=document_id,
                filename=filename,
                document_type=document_type,
                status=status,
                extracted_data=extracted_data_dict,
                missing_fields=missing_fields,
                error=None
            )

        except Exception as e:
            logger.exception(f"Document processing failed for {filename}: {str(e)}")
            return DocumentProcessResult(
                document_id=document_id,
                filename=filename,
                document_type=document_type,
                status=DocumentExtractionStatus.NEEDS_REVIEW,
                extracted_data={},
                missing_fields=[],
                error=f"Extraction failure: {str(e)}"
            )


# Singleton service instance
document_service = DocumentProcessingService()

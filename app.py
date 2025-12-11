import streamlit as st
import logging
import json
from typing import Dict, List
import pandas as pd
from pathlib import Path

# Import our custom modules
from config import Config, setup_logging
from pdf_processor import PDFProcessor
from s3_uploader import S3Uploader
from lambda_processor import LambdaProcessor
from clause_extractor import ClauseExtractor
from bedrock_clause_extractor import BedrockClauseExtractor

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Configure Streamlit page
st.set_page_config(
    page_title="Legal Document Analyzer",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

class LegalDocumentAnalyzerApp:
    """Main application class for the Legal Document Analyzer"""
    
    def __init__(self):
        self.config = Config()
        self.pdf_processor = PDFProcessor(self.config.MAX_PDF_SIZE_MB)
        self.s3_uploader = S3Uploader()
        self.lambda_processor = LambdaProcessor()
        self.clause_extractor = ClauseExtractor()
        try:
            self.bedrock_extractor = BedrockClauseExtractor()
        except Exception as e:
            self.bedrock_extractor = None
            logger.warning(f"Bedrock extractor not available: {str(e)}")
    
    def run(self):
        """Run the Streamlit application"""
        
        # Main title
        st.title("⚖️ Legal Document Analyzer")
        st.markdown("Upload a legal document (PDF) to automatically extract and categorize different types of clauses.")
        
        # Sidebar configuration
        with st.sidebar:
            st.header("⚙️ Configuration")
            
            # Processing method selection
            processing_options = ["Local Regex Processing"]
            
            if self.bedrock_extractor is not None:
                processing_options.append("Bedrock LLM Processing")
            else:
                st.warning("⚠️ Bedrock LLM not configured. Set up AWS credentials to use Claude.")
            
            processing_options.append("AWS Lambda Processing")
            
            processing_method = st.radio(
                "Processing Method",
                processing_options,
                help="Choose between local regex, Bedrock LLM, or AWS Lambda cloud processing"
            )
            
            # Always simplify for Bedrock LLM (removed checkbox - always enabled)
            simplify_clauses = processing_method == "Bedrock LLM Processing" and self.bedrock_extractor is not None
            if simplify_clauses:
                st.info("🧠 **AI Simplification:** Automatically converts legal jargon to plain English")
            
            # Clause types selection  
            st.subheader("Clause Types to Extract")
            selected_clause_types = []
            
            for clause_type in self.config.CLAUSE_TYPES:
                if st.checkbox(clause_type, value=True):
                    selected_clause_types.append(clause_type)
            
            if st.button("Select All"):
                selected_clause_types = self.config.CLAUSE_TYPES
            
            if st.button("Deselect All"):
                selected_clause_types = []
        
        # Main content area
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.header("📄 Document Upload")
            
            # File upload
            uploaded_file = st.file_uploader(
                "Choose a PDF file",
                type="pdf",
                help=f"Maximum file size: {self.config.MAX_PDF_SIZE_MB} MB"
            )
            
            if uploaded_file is not None:
                # Display file information
                st.success(f"✅ File uploaded: {uploaded_file.name}")
                st.info(f"📊 File size: {uploaded_file.size / 1024 / 1024:.2f} MB")
                
                # Process button
                if st.button("🚀 Analyze Document", type="primary"):
                    self.process_document(uploaded_file, selected_clause_types, processing_method, simplify_clauses)
        
        with col2:
            st.header("📋 Analysis Results")
            
            # Display results if available
            if "analysis_results" in st.session_state:
                self.display_results(st.session_state.analysis_results)
            else:
                st.info("Upload and analyze a document to see results here.")
    
    def process_document(self, uploaded_file, clause_types: List[str], processing_method: str, simplify_clauses: bool = False):
        """Process the uploaded document with live thinking display"""
        
        # Create status containers for real-time updates
        status_container = st.empty()
        progress_container = st.empty()
        thinking_container = st.empty()
        
        try:
            # Initialize status
            status_container.info("🚀 **Starting document analysis...**")
            
            if processing_method == "Local Regex Processing":
                results = self._process_locally(uploaded_file, clause_types, status_container, progress_container, thinking_container)
            elif processing_method == "Bedrock LLM Processing":
                results = self._process_with_bedrock(uploaded_file, clause_types, status_container, progress_container, thinking_container, simplify_clauses)
            elif processing_method == "AWS Lambda Processing":
                results = self._process_with_lambda(uploaded_file, clause_types, status_container, progress_container, thinking_container)
            else:
                raise ValueError(f"Unknown processing method: {processing_method}")
            
            # Clear status containers and show success
            status_container.empty()
            progress_container.empty()
            thinking_container.empty()
            
            st.session_state.analysis_results = results
            st.success("✅ Document processed successfully!")
            
        except Exception as e:
            logger.error(f"Error processing document: {str(e)}")
            
            # Clear status containers and show error
            status_container.empty()
            progress_container.empty()
            thinking_container.empty()
            
            st.error(f"❌ Error processing document: {str(e)}")
    
    def _process_locally(self, uploaded_file, clause_types: List[str], status_container, progress_container, thinking_container) -> Dict:
        """Process document locally using regex with live thinking updates"""
        
        # Step 1: Extract text
        thinking_container.info("**Processing:** Reading PDF and extracting text content...")
        pdf_bytes = uploaded_file.read()
        text = self.pdf_processor.extract_text_from_bytes(pdf_bytes)
        status_container.success(f"**Text Extracted:** {len(text):,} characters ready for analysis")
        
        # Step 2: Analyze structure
        thinking_container.info("**Analyzing:** Document structure and identifying clause patterns...")
        import time; time.sleep(0.5)  # Brief pause so user can see the thinking
        
        # Step 3: Extract clauses
        thinking_container.info("**Extracting:** Applying pattern recognition to identify clause types...")
        extracted_clauses = self.clause_extractor.extract_clauses_by_type(text, clause_types)
        
        # Step 4: Detailed analysis
        thinking_container.info("**Processing:** Performing detailed clause analysis and categorization...")
        detailed_clauses = self.clause_extractor.split_into_clauses(text)
        grouped_detailed = self.clause_extractor.group_clauses_by_type(detailed_clauses)
        
        # Final status
        status_container.success(f"**Analysis Complete:** Found {len(detailed_clauses)} clauses across {len(grouped_detailed)} categories")
        
        return {
            'success': True,
            'processing_method': 'local',
            'document_info': {
                'filename': uploaded_file.name,
                'file_size': uploaded_file.size,
                'text_length': len(text),
                'total_clauses_found': len(detailed_clauses)
            },
            'extracted_clauses': extracted_clauses,
            'detailed_clauses': {
                clause_type: [
                    {
                        'clause_name': clause.clause_name,
                        'content': clause.content,
                        'clause_type': clause.clause_type,
                        'section_number': clause.section_number,
                        'page_reference': clause.page_reference
                    }
                    for clause in clauses
                ]
                for clause_type, clauses in grouped_detailed.items()
            },
            'processing_metadata': {
                'extraction_method': 'regex_deterministic_local',
                'total_clauses_found': len(detailed_clauses),
                'clause_types_found': list(grouped_detailed.keys()),
                'clause_types_requested': clause_types
            }
        }
    
    def _process_with_bedrock(self, uploaded_file, clause_types: List[str], status_container, progress_container, thinking_container, simplify_clauses: bool = False) -> Dict:
        """Process document using Bedrock LLM with live thinking updates"""
        
        # Step 1: Extract text
        thinking_container.info("**Processing:** Reading PDF and extracting document text...")
        pdf_bytes = uploaded_file.read()
        text = self.pdf_processor.extract_text_from_bytes(pdf_bytes)
        status_container.success(f"**Text Extracted:** {len(text):,} characters ready for AI analysis")
        
        # Step 2: Analyze document size and strategy
        if len(text) > 5000:
            thinking_container.info(f"**Analyzing:** Large document detected ({len(text):,} chars). Preparing parallel AI processing...")
            estimated_chunks = (len(text) // 5000) + 1
            progress_container.info(f"**Strategy:** Split into {estimated_chunks} chunks, process with 10 parallel AI workers")
        else:
            thinking_container.info("**Processing:** Small document - single AI analysis call...")
        
        # Step 3: AI Processing
        thinking_container.info("**AI Processing:** Connecting to Claude AI for legal document analysis...")
        status_container.info("**Claude AI:** Analyzing document structure and extracting clauses...")
        
        extracted_clauses = self.bedrock_extractor.extract_clauses_by_type(text, clause_types)
        
        # Step 4: Detailed analysis (with optional simplification)
        if simplify_clauses:
            thinking_container.info("**AI Simplification:** Converting legal jargon to plain English (parallel processing)...")
            status_container.info("**Claude AI:** Generating plain English explanations for all clauses...")
        else:
            thinking_container.info("**AI Analysis:** Performing detailed clause categorization and extraction...")
        
        detailed_clauses = self.bedrock_extractor.get_detailed_clauses(text, simplify_for_non_lawyers=simplify_clauses)
        
        # Final status
        if simplify_clauses:
            status_container.success(f"**Analysis Complete:** {len(detailed_clauses)} clauses extracted with plain English explanations")
        else:
            status_container.success(f"**Analysis Complete:** {len(detailed_clauses)} clauses extracted and categorized")
        
        return {
            'success': True,
            'processing_method': 'bedrock_llm',
            'document_info': {
                'filename': uploaded_file.name,
                'file_size': uploaded_file.size,
                'text_length': len(text),
                'total_clauses_found': len(detailed_clauses)
            },
            'extracted_clauses': extracted_clauses,
            'detailed_clauses': {
                'LLM Extracted': detailed_clauses
            },
            'processing_metadata': {
                'extraction_method': 'bedrock_claude_llm',
                'total_clauses_found': len(detailed_clauses),
                'clause_types_found': ['LLM Extracted'],
                'clause_types_requested': clause_types
            }
        }
    
    def _process_with_lambda(self, uploaded_file, clause_types: List[str], status_container, progress_container, thinking_container) -> Dict:
        """Process document using AWS Lambda with live thinking updates"""
        
        # Step 1: Prepare for cloud processing
        thinking_container.info("🤔 **Thinking:** Preparing document for cloud processing...")
        pdf_bytes = uploaded_file.read()
        file_size_mb = len(pdf_bytes) / 1024 / 1024
        
        # Step 2: Upload to S3
        thinking_container.info("☁️ **Cloud Thinking:** Uploading document to AWS S3 for serverless processing...")
        status_container.info(f"⬆️ **Uploading:** {file_size_mb:.1f}MB to S3...")
        
        upload_result = self.s3_uploader.upload_pdf_bytes(pdf_bytes, uploaded_file.name)
        
        if not upload_result['success']:
            raise Exception("Failed to upload file to S3")
        
        status_container.success(f"✅ **S3 Upload Complete:** {upload_result['s3_key']}")
        
        # Step 3: Invoke Lambda
        thinking_container.info("🚀 **Cloud Thinking:** Triggering AWS Lambda function for serverless document analysis...")
        progress_container.info("⚡ **Lambda Processing:** Running regex analysis on AWS infrastructure...")
        
        lambda_result = self.lambda_processor.invoke_document_processor(
            upload_result['bucket'],
            upload_result['s3_key']
        )
        
        # Final status
        status_container.success("🎯 **Lambda Processing Complete:** Document analyzed using AWS serverless infrastructure!")
        
        # Add upload info to result
        result = lambda_result['body']
        result['s3_info'] = {
            'bucket': upload_result['bucket'],
            's3_key': upload_result['s3_key'],
            'download_url': upload_result['download_url']
        }
        result['processing_method'] = 'lambda'
        
        return result
    
    def display_results(self, results: Dict):
        """Display analysis results"""
        
        if not results.get('success', False):
            st.error(f"❌ Processing failed: {results.get('error', 'Unknown error')}")
            return
        
        # Document information
        doc_info = results.get('document_info', {})
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📄 Text Length", f"{doc_info.get('text_length', 0):,} chars")
        with col2:
            st.metric("📝 Total Clauses", doc_info.get('total_clauses_found', 0))
        with col3:
            st.metric("🔍 Processing Method", results.get('processing_method', 'unknown').title())
        
        # Processing metadata
        metadata = results.get('processing_metadata', {})
        if metadata:
            with st.expander("📊 Processing Details"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Clause Types Found:**")
                    for clause_type in metadata.get('clause_types_found', []):
                        st.write(f"• {clause_type}")
                
                with col2:
                    st.write("**Extraction Method:**")
                    st.write(metadata.get('extraction_method', 'N/A'))
        
        # Extracted clauses by type
        st.subheader("📋 Extracted Clauses by Type")
        
        extracted_clauses = results.get('extracted_clauses', {})
        
        # Create tabs for each clause type
        clause_types_with_content = [ct for ct, clauses in extracted_clauses.items() if clauses]
        
        if clause_types_with_content:
            tabs = st.tabs(clause_types_with_content)
            
            for i, clause_type in enumerate(clause_types_with_content):
                with tabs[i]:
                    clauses = extracted_clauses[clause_type]
                    
                    st.write(f"**Found {len(clauses)} {clause_type} clause(s):**")
                    
                    for j, clause in enumerate(clauses, 1):
                        with st.expander(f"Clause {j}", expanded=j == 1):
                            st.write(clause)
        else:
            st.warning("⚠️ No clauses found matching the selected types.")
        
        # Detailed clause information
        detailed_clauses = results.get('detailed_clauses', {})
        if detailed_clauses:
            st.subheader("🔍 Detailed Clause Analysis")
            
            # Check if we have simplified clauses (they contain extra fields)
            first_clause = next(iter(detailed_clauses.values()))[0] if detailed_clauses else {}
            has_simplification = 'simple_title' in first_clause
            
            if has_simplification:
                # Enhanced display for simplified clauses
                for clause_type, clauses in detailed_clauses.items():
                    for i, clause in enumerate(clauses, 1):
                        with st.expander(f"📋 {clause.get('simple_title', clause['clause_name'])}", expanded=i == 1):
                            
                            col1, col2 = st.columns([2, 1])
                            
                            with col1:
                                # Plain English Summary
                                st.markdown("### 📝 **Plain English Summary**")
                                st.info(clause.get('plain_english_summary', 'Not available'))
                                
                                # Key Points
                                key_points = clause.get('key_points', [])
                                if key_points:
                                    st.markdown("### 🎯 **Key Points**")
                                    for point in key_points:
                                        st.markdown(f"• {point}")
                                
                                # Potential Impact
                                impact = clause.get('potential_impact', '')
                                if impact:
                                    st.markdown("### ⚖️ **What This Means For You**")
                                    st.warning(impact)
                            
                            with col2:
                                # Red Flags
                                red_flags = clause.get('red_flags', 'None identified')
                                st.markdown("### 🚨 **Red Flags**")
                                if red_flags and red_flags.lower() != 'none identified':
                                    st.error(red_flags)
                                else:
                                    st.success("✅ No major concerns identified")
                                
                                # Clause Details
                                st.markdown("### 📊 **Details**")
                                st.write(f"**Type:** {clause.get('clause_type', 'N/A')}")
                                st.write(f"**Length:** {len(clause['content']):,} chars")
                            
                            # Original Legal Text (collapsible)
                            with st.expander("📜 Original Legal Text"):
                                st.code(clause['content'], language='text')
            else:
                # Standard display for non-simplified clauses
                with st.expander("📊 Clause Summary Table"):
                    summary_data = []
                    for clause_type, clauses in detailed_clauses.items():
                        for clause in clauses:
                            summary_data.append({
                                'Type': clause_type,
                                'Name': clause['clause_name'][:50] + '...' if len(clause['clause_name']) > 50 else clause['clause_name'],
                                'Section': clause.get('section_number', 'N/A'),
                                'Page': clause.get('page_reference', 'N/A'),
                                'Content Length': len(clause['content'])
                            })
                    
                    if summary_data:
                        df = pd.DataFrame(summary_data)
                        st.dataframe(df, use_container_width=True)
                
                # Individual clause display
                for clause_type, clauses in detailed_clauses.items():
                    for i, clause in enumerate(clauses, 1):
                        with st.expander(f"📋 {clause['clause_name']}", expanded=i == 1):
                            st.write(f"**Type:** {clause.get('clause_type', 'N/A')}")
                            st.write(f"**Content Length:** {len(clause['content']):,} characters")
                            st.code(clause['content'], language='text')
        
        # Export options
        st.subheader("💾 Export Options")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📄 Download as JSON"):
                json_str = json.dumps(results, indent=2)
                st.download_button(
                    label="Download JSON",
                    data=json_str,
                    file_name=f"analysis_results_{doc_info.get('filename', 'document')}.json",
                    mime="application/json"
                )
        
        with col2:
            if st.button("📊 Download Summary CSV") and detailed_clauses:
                summary_data = []
                for clause_type, clauses in detailed_clauses.items():
                    for clause in clauses:
                        summary_data.append({
                            'Type': clause_type,
                            'Clause_Name': clause['clause_name'],
                            'Section_Number': clause.get('section_number', ''),
                            'Page_Reference': clause.get('page_reference', ''),
                            'Content': clause['content']
                        })
                
                if summary_data:
                    df = pd.DataFrame(summary_data)
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="Download CSV",
                        data=csv,
                        file_name=f"clause_summary_{doc_info.get('filename', 'document')}.csv",
                        mime="text/csv"
                    )

def main():
    """Main function to run the application"""
    try:
        app = LegalDocumentAnalyzerApp()
        app.run()
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error(f"❌ Application error: {str(e)}")
        st.info("Please check your configuration and try again.")

if __name__ == "__main__":
    main()

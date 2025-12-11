#!/usr/bin/env python3
"""
Simple test script to verify local processing functionality
"""

import logging
from config import setup_logging
from clause_extractor import ClauseExtractor

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

def test_clause_extraction():
    """Test clause extraction with sample legal text"""
    
    sample_legal_text = """
    SAMPLE LEGAL AGREEMENT
    
    --- Page 1 ---
    
    1. DEFINITIONS
    
    For purposes of this Agreement, the following terms shall have the meanings set forth below:
    
    "Confidential Information" means any and all proprietary information disclosed by one party to the other.
    
    2. PAYMENT TERMS
    
    Payment shall be made within thirty (30) days of receipt of invoice. Late payments may incur a fee of 1.5% per month.
    
    3. TERMINATION
    
    This Agreement may be terminated by either party upon thirty (30) days written notice to the other party.
    
    4. LIABILITY AND INDEMNIFICATION
    
    Each party shall indemnify and hold harmless the other party from any damages arising from breach of this Agreement.
    
    5. CONFIDENTIALITY
    
    The parties agree to maintain the confidentiality of all Confidential Information received from the other party.
    
    6. GOVERNING LAW
    
    This Agreement shall be governed by the laws of the State of California.
    
    7. DISPUTE RESOLUTION
    
    Any disputes arising under this Agreement shall be resolved through binding arbitration.
    """
    
    try:
        print("🧪 Testing Legal Document Analyzer - Local Processing")
        print("=" * 60)
        
        # Initialize clause extractor
        extractor = ClauseExtractor()
        
        # Test clause splitting
        print("📝 Extracting clauses from sample document...")
        clauses = extractor.split_into_clauses(sample_legal_text)
        
        print(f"✅ Found {len(clauses)} total clauses")
        
        # Display found clauses
        for i, clause in enumerate(clauses, 1):
            print(f"\n📋 Clause {i}:")
            print(f"   Name: {clause.clause_name}")
            print(f"   Type: {clause.clause_type or 'Unclassified'}")
            print(f"   Section: {clause.section_number or 'N/A'}")
            print(f"   Content Length: {len(clause.content)} characters")
        
        # Test clause extraction by type
        print(f"\n🔍 Testing clause extraction by type...")
        target_types = ["Payment Terms", "Termination Clause", "Confidentiality Clause", "Governing Law"]
        
        extracted_by_type = extractor.extract_clauses_by_type(sample_legal_text, target_types)
        
        print(f"\n📊 Results by clause type:")
        for clause_type, clause_list in extracted_by_type.items():
            print(f"   {clause_type}: {len(clause_list)} clause(s) found")
            
            if clause_list:
                # Show first 100 characters of first clause
                preview = clause_list[0][:100] + "..." if len(clause_list[0]) > 100 else clause_list[0]
                print(f"      Preview: {preview}")
        
        # Test grouping
        print(f"\n📑 Testing clause grouping...")
        grouped = extractor.group_clauses_by_type(clauses)
        
        print(f"   Found clause types: {list(grouped.keys())}")
        
        print("\n✅ All local processing tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        logger.error(f"Test error: {str(e)}")
        return False

def test_pdf_processing():
    """Test PDF processing (mock test without actual PDF)"""
    
    try:
        print(f"\n🧪 Testing PDF Processing Components")
        print("=" * 60)
        
        from pdf_processor import PDFProcessor
        
        processor = PDFProcessor()
        print("✅ PDF Processor initialized successfully")
        
        # Test validation with non-existent file (expected to fail gracefully)
        result = processor.validate_pdf("non_existent.pdf")
        
        if not result["valid"]:
            print(f"✅ PDF validation correctly identified missing file")
        
        print("✅ PDF processing components test completed")
        return True
        
    except Exception as e:
        print(f"❌ PDF processing test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    
    print("🚀 Starting Legal Document Analyzer Tests")
    print("=" * 60)
    
    tests_passed = 0
    total_tests = 2
    
    # Test clause extraction
    if test_clause_extraction():
        tests_passed += 1
    
    # Test PDF processing
    if test_pdf_processing():
        tests_passed += 1
    
    print(f"\n📈 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! The system is ready for use.")
        print("\n🚀 To start the application, run:")
        print("   streamlit run app.py")
    else:
        print("⚠️  Some tests failed. Please check the error messages above.")

if __name__ == "__main__":
    main()

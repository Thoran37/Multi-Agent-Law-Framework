import requests
import sys
import time
from datetime import datetime
from pathlib import Path

class LegalCourtSimulatorTester:
    def __init__(self, base_url="https://moot-court-ai.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.case_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.sample_case_file = "/tmp/sample_case.txt"

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, timeout=60)
                elif data:
                    headers['Content-Type'] = 'application/json'
                    response = requests.post(url, json=data, headers=headers, timeout=60)
                else:
                    response = requests.post(url, headers=headers, timeout=60)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    print(f"   Response keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'Non-dict response'}")
                    return True, response_data
                except:
                    return True, response.text
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}...")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_root_endpoint(self):
        """Test API root endpoint"""
        success, response = self.run_test(
            "API Root",
            "GET",
            "",
            200
        )
        return success

    def test_upload_document(self):
        """Test document upload"""
        if not Path(self.sample_case_file).exists():
            print(f"❌ Sample case file not found: {self.sample_case_file}")
            return False
        
        with open(self.sample_case_file, 'rb') as f:
            files = {'file': ('sample_case.txt', f, 'text/plain')}
            success, response = self.run_test(
                "Upload Document",
                "POST",
                "upload",
                200,
                files=files
            )
        
        if success and 'case_id' in response:
            self.case_id = response['case_id']
            print(f"   Case ID: {self.case_id}")
            return True
        return False

    def test_process_case(self):
        """Test case processing"""
        if not self.case_id:
            print("❌ No case_id available for processing")
            return False
        
        success, response = self.run_test(
            "Process Case",
            "POST",
            f"process-case/{self.case_id}",
            200
        )
        
        if success:
            required_fields = ['facts', 'issues', 'holding']
            for field in required_fields:
                if field not in response:
                    print(f"❌ Missing required field: {field}")
                    return False
            print(f"   Facts length: {len(response.get('facts', ''))}")
            print(f"   Issues length: {len(response.get('issues', ''))}")
            print(f"   Holding length: {len(response.get('holding', ''))}")
        
        return success

    def test_baseline_prediction(self):
        """Test baseline classifier prediction"""
        if not self.case_id:
            print("❌ No case_id available for prediction")
            return False
        
        success, response = self.run_test(
            "Baseline Prediction",
            "POST",
            f"predict/{self.case_id}",
            200
        )
        
        if success:
            required_fields = ['prediction', 'confidence', 'method']
            for field in required_fields:
                if field not in response:
                    print(f"❌ Missing required field: {field}")
                    return False
            print(f"   Prediction: {response.get('prediction')}")
            print(f"   Confidence: {response.get('confidence')}%")
        
        return success

    def test_simulation(self):
        """Test multi-agent simulation"""
        if not self.case_id:
            print("❌ No case_id available for simulation")
            return False
        
        print("   Note: This may take 30-60 seconds due to LLM processing...")
        success, response = self.run_test(
            "Multi-Agent Simulation",
            "POST",
            f"simulate/{self.case_id}?rounds=2",
            200
        )
        
        if success:
            required_fields = ['debate_transcript', 'verdict', 'rounds_completed']
            for field in required_fields:
                if field not in response:
                    print(f"❌ Missing required field: {field}")
                    return False
            
            transcript = response.get('debate_transcript', [])
            verdict = response.get('verdict', {})
            
            print(f"   Rounds completed: {response.get('rounds_completed')}")
            print(f"   Transcript entries: {len(transcript)}")
            print(f"   Verdict: {verdict.get('verdict', 'N/A')}")
            print(f"   Confidence: {verdict.get('confidence', 'N/A')}%")
        
        return success

    def test_bias_audit(self):
        """Test bias audit"""
        if not self.case_id:
            print("❌ No case_id available for audit")
            return False
        
        print("   Note: This may take 15-30 seconds due to LLM processing...")
        success, response = self.run_test(
            "Bias Audit",
            "POST",
            f"audit/{self.case_id}",
            200
        )
        
        if success:
            audit_result = response.get('audit_result', {})
            if 'fairness_score' not in audit_result:
                print("❌ Missing fairness_score in audit result")
                return False
            
            print(f"   Fairness Score: {audit_result.get('fairness_score')}/100")
            print(f"   Biased Terms: {len(audit_result.get('biased_terms', []))}")
            print(f"   Bias Types: {audit_result.get('bias_types', [])}")
        
        return success

    def test_get_case(self):
        """Test retrieving complete case data"""
        if not self.case_id:
            print("❌ No case_id available for retrieval")
            return False
        
        success, response = self.run_test(
            "Get Complete Case",
            "GET",
            f"case/{self.case_id}",
            200
        )
        
        if success:
            expected_sections = ['raw_text', 'facts', 'issues', 'holding', 'baseline_prediction', 'simulation', 'audit']
            found_sections = [section for section in expected_sections if section in response]
            print(f"   Found sections: {found_sections}")
        
        return success

    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting Legal Multi-Agent Courtroom Simulator API Tests")
        print(f"   Base URL: {self.base_url}")
        print(f"   Sample file: {self.sample_case_file}")
        
        # Test sequence
        tests = [
            ("API Root", self.test_root_endpoint),
            ("Document Upload", self.test_upload_document),
            ("Case Processing", self.test_process_case),
            ("Baseline Prediction", self.test_baseline_prediction),
            ("Multi-Agent Simulation", self.test_simulation),
            ("Bias Audit", self.test_bias_audit),
            ("Complete Case Retrieval", self.test_get_case)
        ]
        
        for test_name, test_func in tests:
            try:
                success = test_func()
                if not success:
                    print(f"\n⚠️  Test '{test_name}' failed - stopping test suite")
                    break
            except Exception as e:
                print(f"\n💥 Test '{test_name}' crashed: {str(e)}")
                break
        
        # Print final results
        print(f"\n📊 Test Results:")
        print(f"   Tests Run: {self.tests_run}")
        print(f"   Tests Passed: {self.tests_passed}")
        print(f"   Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        if self.case_id:
            print(f"   Final Case ID: {self.case_id}")
        
        return self.tests_passed == self.tests_run

def main():
    tester = LegalCourtSimulatorTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
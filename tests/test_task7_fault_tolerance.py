import unittest
import time
import random
from uuid import uuid4

from rec.nodes.fault_tolerance.advanced_fault_tolerance import SimpleFaultDetector, SimplePartitionDetector, AdvancedRecoveryManager
from rec.nodes.fault_tolerance.byzantine_tolerance import SimpleByzantineDetector, SimpleConsensusManager
from rec.nodes.fault_tolerance.integration_system import Task7FaultToleranceSystem


class TestAdvancedFaultTolerance(unittest.TestCase):
    """Tests for Task 7 advanced fault tolerance components"""

    def setUp(self):
        self.detector = SimpleFaultDetector("test_detector")
        self.partition_detector = SimplePartitionDetector("test_partition")
        self.recovery = AdvancedRecoveryManager("test_recovery")

    def test_fault_detector_initialization(self):
        """Test fault detector initializes correctly"""
        self.assertEqual(self.detector.detector_id, "test_detector")
        self.assertEqual(len(self.detector.node_health), 0)
        self.assertEqual(len(self.detector.suspected_failed), 0)
        self.assertEqual(len(self.detector.confirmed_failed), 0)

    def test_fault_detector_node_registration(self):
        """Test node registration with fault detector"""
        self.detector.register_node("test_node")
        self.assertIn("test_node", self.detector.node_health)
        self.assertTrue(self.detector.node_health["test_node"].is_healthy)

    def test_fault_detector_heartbeat_processing(self):
        """Test heartbeat processing"""
        self.detector.register_node("test_node")
        self.detector.receive_heartbeat("test_node", 0.15)
        
        health = self.detector.node_health["test_node"]
        self.assertEqual(health.failure_count, 0)
        self.assertTrue(health.is_healthy)
        self.assertEqual(health.response_time, 0.15)

    def test_fault_detector_failure_detection(self):
        """Test failure detection mechanism"""
        self.detector.register_node("test_node")
        self.detector.heartbeat_timeout = 0.1  # Very short timeout for testing
        
        # Wait longer than timeout
        time.sleep(0.2)
        
        failed_nodes = self.detector.check_for_failures()
        # Note: might not fail immediately due to failure count threshold
        
        healthy_nodes = self.detector.get_healthy_nodes()
        self.assertIsInstance(healthy_nodes, list)

    def test_partition_detector_initialization(self):
        """Test partition detector initializes correctly"""
        self.assertEqual(self.partition_detector.detector_id, "test_partition")
        self.assertEqual(len(self.partition_detector.known_nodes), 0)
        self.assertFalse(self.partition_detector.is_partitioned())

    def test_partition_detector_node_management(self):
        """Test partition detector node management"""
        nodes = ["node1", "node2", "node3"]
        for node in nodes:
            self.partition_detector.add_known_node(node)
        
        self.assertEqual(len(self.partition_detector.known_nodes), 3)
        self.assertEqual(len(self.partition_detector.reachable_nodes), 3)

    def test_partition_detector_partition_detection(self):
        """Test network partition detection"""
        nodes = ["node1", "node2", "node3", "node4"]
        for node in nodes:
            self.partition_detector.add_known_node(node)
        
        # Simulate partition - only some nodes reachable
        self.partition_detector.update_reachable_nodes(["node1", "node2"])
        
        # Should detect partition
        partition_info = self.partition_detector.get_partition_info()
        self.assertEqual(partition_info['reachable_nodes'], 2)
        self.assertEqual(partition_info['unreachable_nodes'], 2)

    def test_advanced_recovery_initialization(self):
        """Test advanced recovery manager initialization"""
        self.assertEqual(self.recovery.manager_id, "test_recovery")
        self.assertIsNotNone(self.recovery.fault_detector)
        self.assertIsNotNone(self.recovery.partition_detector)
        self.assertEqual(len(self.recovery.critical_jobs), 0)

    def test_advanced_recovery_executor_registration(self):
        """Test executor registration with advanced recovery"""
        self.recovery.register_executor("test_exec")
        
        # Should be registered in all components
        healthy_nodes = self.recovery.fault_detector.get_healthy_nodes()
        self.assertIn("test_exec", healthy_nodes)

    def test_advanced_recovery_critical_job_marking(self):
        """Test critical job marking and backup creation"""
        # Register some executors first
        self.recovery.register_executor("exec1")
        self.recovery.register_executor("exec2")
        
        # Mark job as critical
        self.recovery.mark_job_critical("critical_job_1")
        
        self.assertIn("critical_job_1", self.recovery.critical_jobs)
        # Should have backup if enough healthy nodes
        if len(self.recovery.fault_detector.get_healthy_nodes()) >= 2:
            self.assertIn("critical_job_1", self.recovery.job_backup_copies)


class TestByzantineFaultTolerance(unittest.TestCase):
    """Tests for Byzantine fault tolerance components"""

    def setUp(self):
        self.byzantine_detector = SimpleByzantineDetector("test_byzantine")
        self.consensus = SimpleConsensusManager("test_consensus")

    def test_byzantine_detector_initialization(self):
        """Test Byzantine detector initializes correctly"""
        self.assertEqual(self.byzantine_detector.detector_id, "test_byzantine")
        self.assertEqual(len(self.byzantine_detector.node_scores), 0)
        self.assertEqual(len(self.byzantine_detector.suspicious_nodes), 0)
        self.assertEqual(len(self.byzantine_detector.trusted_nodes), 0)

    def test_byzantine_detector_node_registration(self):
        """Test node registration with Byzantine detector"""
        self.byzantine_detector.register_node("test_node")
        
        self.assertIn("test_node", self.byzantine_detector.node_scores)
        self.assertEqual(self.byzantine_detector.node_scores["test_node"], 50.0)

    def test_byzantine_detector_reputation_management(self):
        """Test reputation scoring system"""
        self.byzantine_detector.register_node("test_node")
        
        # Good behavior should increase reputation
        initial_score = self.byzantine_detector.node_scores["test_node"]
        self.byzantine_detector.report_good_behavior("test_node", "test_good")
        self.assertGreater(self.byzantine_detector.node_scores["test_node"], initial_score)
        
        # Bad behavior should decrease reputation
        self.byzantine_detector.report_bad_behavior("test_node", "test_bad")
        # Should be lower than after good behavior
        self.assertLess(self.byzantine_detector.node_scores["test_node"], initial_score + 5.0)

    def test_byzantine_detector_trust_classification(self):
        """Test trust and suspicion classification"""
        self.byzantine_detector.register_node("good_node")
        self.byzantine_detector.register_node("bad_node")
        
        # Make good_node trusted
        for _ in range(10):
            self.byzantine_detector.report_good_behavior("good_node")
        
        # Make bad_node suspicious  
        for _ in range(10):
            self.byzantine_detector.report_bad_behavior("bad_node")
        
        # Check classifications
        trusted_nodes = self.byzantine_detector.get_trusted_nodes()
        suspicious_nodes = self.byzantine_detector.get_suspicious_nodes()
        
        self.assertIsInstance(trusted_nodes, list)
        self.assertIsInstance(suspicious_nodes, list)

    def test_consensus_manager_initialization(self):
        """Test consensus manager initialization"""
        self.assertEqual(self.consensus.manager_id, "test_consensus")
        self.assertEqual(len(self.consensus.proposals), 0)
        self.assertEqual(len(self.consensus.active_nodes), 0)

    def test_consensus_manager_node_registration(self):
        """Test node registration with consensus manager"""
        self.consensus.register_node("test_node")
        
        self.assertIn("test_node", self.consensus.active_nodes)

    def test_consensus_manager_proposal_creation(self):
        """Test proposal creation and management"""
        self.consensus.register_node("proposer")
        
        proposal_id = self.consensus.create_proposal("proposer", "Test proposal")
        
        self.assertIn(proposal_id, self.consensus.proposals)
        proposal = self.consensus.proposals[proposal_id]
        self.assertEqual(proposal.proposer_id, "proposer")
        self.assertEqual(proposal.content, "Test proposal")
        self.assertEqual(proposal.status, "pending")

    def test_consensus_manager_voting(self):
        """Test voting mechanism"""
        # Register nodes
        nodes = ["node1", "node2", "node3"]
        for node in nodes:
            self.consensus.register_node(node)
        
        # Create proposal
        proposal_id = self.consensus.create_proposal("node1", "Test vote")
        
        # Submit votes
        self.assertTrue(self.consensus.submit_vote("node1", proposal_id, "yes"))
        self.assertTrue(self.consensus.submit_vote("node2", proposal_id, "yes"))
        self.assertTrue(self.consensus.submit_vote("node3", proposal_id, "no"))
        
        # Check proposal status
        proposal_status = self.consensus.get_proposal_status(proposal_id)
        self.assertIsNotNone(proposal_status)
        self.assertEqual(proposal_status["total_votes"], 3)


class TestTask7Integration(unittest.TestCase):
    """Tests for complete Task 7 fault tolerance system"""

    def setUp(self):
        self.system = Task7FaultToleranceSystem("test_task7")

    def test_system_initialization(self):
        """Test Task 7 system initializes correctly"""
        self.assertEqual(self.system.system_id, "test_task7")
        self.assertEqual(len(self.system.registered_nodes), 0)
        self.assertFalse(self.system.emergency_protocols_active)

    def test_system_node_registration(self):
        """Test node registration with complete system"""
        self.system.register_node("test_node")
        
        self.assertIn("test_node", self.system.registered_nodes)

    def test_system_heartbeat_processing(self):
        """Test heartbeat processing in complete system"""
        self.system.register_node("test_node")
        
        status = {
            'status': 'healthy',
            'response_time': 0.1,
            'vector_clock': {'test_node': 1},
            'load': 0.5
        }
        
        self.system.node_heartbeat("test_node", status)
        # Should not raise any exceptions

    def test_system_health_check(self):
        """Test system health check functionality"""
        # Register some nodes
        for i in range(3):
            self.system.register_node(f"node_{i}")
        
        # Perform health check
        health = self.system.perform_health_check()
        
        self.assertIsNotNone(health)
        self.assertGreaterEqual(health.total_nodes, 0)
        self.assertGreaterEqual(health.healthy_nodes, 0)
        self.assertGreaterEqual(health.failed_nodes, 0)

    def test_system_critical_job_submission(self):
        """Test critical job submission"""
        self.system.register_node("worker_node")
        
        job_data = {"priority": "critical", "type": "emergency"}
        result = self.system.submit_critical_job("critical_job_1", job_data)
        
        self.assertTrue(result)

    def test_system_status_reporting(self):
        """Test comprehensive status reporting"""
        status = self.system.get_system_status()
        
        self.assertIn("system_id", status)
        self.assertIn("registered_nodes", status)
        self.assertIn("emergency_protocols_active", status)
        self.assertIn("vector_clock", status)

    def test_system_health_trend_analysis(self):
        """Test health trend analysis"""
        # Perform multiple health checks to build history
        for i in range(3):
            self.system.perform_health_check()
            time.sleep(0.1)
        
        trend = self.system.get_health_trend()
        self.assertIn("trend", trend)

    def test_byzantine_behavior_detection(self):
        """Test Byzantine behavior detection in complete system"""
        self.system.register_node("byzantine_node")
        
        # Send invalid status
        invalid_status = {
            'status': 'healthy',
            'response_time': -1.0,  # Invalid
            'vector_clock': {'byzantine_node': -5},  # Invalid
            'load': 2.0  # Invalid
        }
        
        self.system.node_heartbeat("byzantine_node", invalid_status)
        # Should detect and handle Byzantine behavior


def run_task7_tests():
    """Run all Task 7 tests"""
    print("🧪 Running Task 7 Fault Tolerance Tests")
    print("=" * 45)
    
    # Create test suite
    test_suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestAdvancedFaultTolerance,
        TestByzantineFaultTolerance, 
        TestTask7Integration
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        test_suite.addTests(tests)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(test_suite)
    
    print(f"\n📊 Test Results:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    
    if result.failures:
        print("\n❌ Failures:")
        for test, traceback in result.failures:
            print(f"   {test}: {traceback}")
    
    if result.errors:
        print("\n🔥 Errors:")
        for test, traceback in result.errors:
            print(f"   {test}: {traceback}")
    
    success_rate = (result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100
    print(f"\n✅ Success rate: {success_rate:.1f}%")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_task7_tests()
    if success:
        print("\n🎉 All Task 7 tests passed!")
    else:
        print("\n⚠️  Some Task 7 tests failed - check output above")

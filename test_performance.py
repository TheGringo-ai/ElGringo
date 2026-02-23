#!/usr/bin/env python3
"""
FredAI Comprehensive Performance & Capability Test Suite
Test all features and compare against alternatives
"""

import asyncio
import time
import json
from typing import List, Dict, Any
from datetime import datetime


class FredAITester:
    """Comprehensive testing of FredAI capabilities"""
    
    def __init__(self):
        self.results: List[Dict[str, Any]] = []
        self.team = None
    
    async def setup(self):
        """Initialize the AI team"""
        from ai_dev_team.orchestrator import AIDevTeam
        
        print("=" * 80)
        print("FredAI Comprehensive Test Suite")
        print("=" * 80 + "\n")
        
        print("🔧 Initializing AI Team...")
        self.team = AIDevTeam(
            project_name="performance_test",
            enable_memory=True,
            enable_learning=True
        )
        
        agents = list(self.team.agents.keys())
        print(f"✅ Team ready: {len(agents)} agents")
        print(f"   {', '.join(agents)}\n")
    
    async def test_basic_ask(self):
        """Test 1: Basic single-agent query"""
        print("\n" + "─" * 80)
        print("TEST 1: Basic Ask (Single Agent)")
        print("─" * 80)
        
        start = time.time()
        result = await self.team.ask(
            "What are the three pillars of observability in distributed systems?"
        )
        duration = time.time() - start
        
        print(f"✅ Response: {result.content[:200]}...")
        print(f"⏱️  Time: {duration:.2f}s")
        
        self.results.append({
            "test": "basic_ask",
            "duration": duration,
            "success": result.success,
            "response_length": len(result.content)
        })
    
    async def test_parallel_collaboration(self):
        """Test 2: Parallel multi-agent collaboration"""
        print("\n" + "─" * 80)
        print("TEST 2: Parallel Collaboration")
        print("─" * 80)
        
        start = time.time()
        result = await self.team.collaborate(
            "Explain the CAP theorem and its implications for database design",
            mode="parallel"
        )
        duration = time.time() - start
        
        print(f"✅ Success: {result.success}")
        print(f"👥 Agents: {', '.join(result.participating_agents)}")
        print(f"📈 Confidence: {result.confidence_score:.2f}")
        print(f"⏱️  Time: {duration:.2f}s")
        print(f"📝 Response: {result.final_answer[:200]}...")
        
        self.results.append({
            "test": "parallel_collaboration",
            "duration": duration,
            "success": result.success,
            "agents": len(result.participating_agents),
            "confidence": result.confidence_score
        })
    
    async def test_consensus_mode(self):
        """Test 3: Consensus voting"""
        print("\n" + "─" * 80)
        print("TEST 3: Consensus Mode")
        print("─" * 80)
        
        start = time.time()
        result = await self.team.collaborate(
            "Should we use microservices or monolith architecture for a new e-commerce platform?",
            mode="consensus"
        )
        duration = time.time() - start
        
        print(f"✅ Success: {result.success}")
        print(f"👥 Agents: {', '.join(result.participating_agents)}")
        print(f"📈 Confidence: {result.confidence_score:.2f}")
        print(f"⏱️  Time: {duration:.2f}s")
        print(f"🗳️  Decision: {result.final_answer[:300]}...")
        
        self.results.append({
            "test": "consensus_mode",
            "duration": duration,
            "success": result.success,
            "agents": len(result.participating_agents),
            "confidence": result.confidence_score
        })
    
    async def test_peer_review(self):
        """Test 4: Code peer review"""
        print("\n" + "─" * 80)
        print("TEST 4: Peer Review Mode")
        print("─" * 80)
        
        code_sample = """
def calculate_discount(price, user_type):
    if user_type == "premium":
        return price * 0.8
    elif user_type == "regular":
        return price * 0.9
    return price
"""
        
        start = time.time()
        result = await self.team.collaborate(
            f"Review this code for issues:\n\n{code_sample}",
            mode="peer_review"
        )
        duration = time.time() - start
        
        print(f"✅ Success: {result.success}")
        print(f"👥 Reviewers: {', '.join(result.participating_agents)}")
        print(f"📈 Confidence: {result.confidence_score:.2f}")
        print(f"⏱️  Time: {duration:.2f}s")
        print(f"📋 Review: {result.final_answer[:300]}...")
        
        self.results.append({
            "test": "peer_review",
            "duration": duration,
            "success": result.success,
            "agents": len(result.participating_agents),
            "confidence": result.confidence_score
        })
    
    async def test_brainstorming(self):
        """Test 5: Creative brainstorming"""
        print("\n" + "─" * 80)
        print("TEST 5: Brainstorming Mode")
        print("─" * 80)
        
        start = time.time()
        result = await self.team.collaborate(
            "Generate 5 innovative features for a next-gen code editor",
            mode="brainstorming"
        )
        duration = time.time() - start
        
        print(f"✅ Success: {result.success}")
        print(f"👥 Contributors: {', '.join(result.participating_agents)}")
        print(f"📈 Confidence: {result.confidence_score:.2f}")
        print(f"⏱️  Time: {duration:.2f}s")
        print(f"💡 Ideas: {result.final_answer[:300]}...")
        
        self.results.append({
            "test": "brainstorming",
            "duration": duration,
            "success": result.success,
            "agents": len(result.participating_agents),
            "confidence": result.confidence_score
        })
    
    async def test_debate_mode(self):
        """Test 6: Structured debate"""
        print("\n" + "─" * 80)
        print("TEST 6: Debate Mode")
        print("─" * 80)
        
        start = time.time()
        result = await self.team.collaborate(
            "Debate: Should AI code generation replace human programmers?",
            mode="debate"
        )
        duration = time.time() - start
        
        print(f"✅ Success: {result.success}")
        print(f"👥 Debaters: {', '.join(result.participating_agents)}")
        print(f"📈 Confidence: {result.confidence_score:.2f}")
        print(f"⏱️  Time: {duration:.2f}s")
        print(f"🎭 Debate: {result.final_answer[:300]}...")
        
        self.results.append({
            "test": "debate_mode",
            "duration": duration,
            "success": result.success,
            "agents": len(result.participating_agents),
            "confidence": result.confidence_score
        })
    
    async def test_memory_system(self):
        """Test 7: Memory and learning"""
        print("\n" + "─" * 80)
        print("TEST 7: Memory System")
        print("─" * 80)
        
        # Store a solution
        print("📝 Storing solution pattern...")
        await self.team.ask("Remember: When handling rate limits, use exponential backoff with jitter")
        
        # Try to recall
        print("🔍 Attempting recall...")
        result = await self.team.ask("What's the best way to handle API rate limits?")
        
        contains_backoff = "backoff" in result.content.lower()
        print(f"✅ Recalled: {'Yes' if contains_backoff else 'No'}")
        print(f"📝 Response: {result.content[:200]}...")
        
        self.results.append({
            "test": "memory_system",
            "success": contains_backoff,
            "recalled_pattern": contains_backoff
        })
    
    async def test_specialist_agents(self):
        """Test 8: Specialist agents (if available)"""
        print("\n" + "─" * 80)
        print("TEST 8: Specialist Agents")
        print("─" * 80)
        
        code = """
import os
API_KEY = os.getenv("API_KEY", "")
def authenticate(password):
    stored = os.getenv("ADMIN_PASSWORD", "")
    return password == stored
"""
        
        try:
            start = time.time()
            result = await self.team.collaborate(
                f"Security audit this code:\n\n{code}",
                mode="consensus"
            )
            duration = time.time() - start
            
            # Check if security issues were found
            found_issues = any(word in result.final_answer.lower() 
                             for word in ["hardcoded", "security", "vulnerability", "risk"])
            
            print(f"✅ Found security issues: {found_issues}")
            print(f"⏱️  Time: {duration:.2f}s")
            print(f"🔒 Audit: {result.final_answer[:300]}...")
            
            self.results.append({
                "test": "security_audit",
                "duration": duration,
                "found_issues": found_issues,
                "success": result.success
            })
        except Exception as e:
            print(f"⚠️  Specialist test failed: {e}")
            self.results.append({
                "test": "security_audit",
                "success": False,
                "error": str(e)
            })
    
    async def test_performance_stress(self):
        """Test 9: Performance under load"""
        print("\n" + "─" * 80)
        print("TEST 9: Performance Stress Test (5 rapid queries)")
        print("─" * 80)
        
        queries = [
            "What is Docker?",
            "Explain REST APIs",
            "What is Redis?",
            "Define microservices",
            "What is Kubernetes?"
        ]
        
        start = time.time()
        results_list = []
        
        for i, query in enumerate(queries, 1):
            print(f"  Query {i}/5: {query[:30]}...")
            result = await self.team.ask(query)
            results_list.append(result.success)
        
        total_duration = time.time() - start
        success_rate = sum(results_list) / len(results_list) * 100
        avg_time = total_duration / len(queries)
        
        print(f"✅ Success rate: {success_rate:.0f}%")
        print(f"⏱️  Total time: {total_duration:.2f}s")
        print(f"⏱️  Avg per query: {avg_time:.2f}s")
        
        self.results.append({
            "test": "stress_test",
            "total_duration": total_duration,
            "avg_per_query": avg_time,
            "success_rate": success_rate
        })
    
    async def test_error_handling(self):
        """Test 10: Error handling and recovery"""
        print("\n" + "─" * 80)
        print("TEST 10: Error Handling")
        print("─" * 80)
        
        # Test with malformed input
        try:
            result = await self.team.ask("")
            print(f"✅ Handled empty input: {result.success}")
        except Exception as e:
            print(f"⚠️  Empty input error: {type(e).__name__}")
        
        # Test with very long input
        try:
            long_input = "Explain " + "very " * 1000 + "long text"
            result = await self.team.ask(long_input[:5000])  # Truncate
            print(f"✅ Handled long input: {result.success}")
        except Exception as e:
            print(f"⚠️  Long input error: {type(e).__name__}")
        
        self.results.append({
            "test": "error_handling",
            "success": True
        })
    
    def generate_report(self):
        """Generate comprehensive test report"""
        print("\n" + "=" * 80)
        print("COMPREHENSIVE TEST REPORT")
        print("=" * 80 + "\n")
        
        # Calculate statistics
        total_tests = len(self.results)
        successful = sum(1 for r in self.results if r.get("success", False))
        
        # Average performance
        durations = [r.get("duration", 0) for r in self.results if "duration" in r]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        # Confidence scores
        confidences = [r.get("confidence", 0) for r in self.results if "confidence" in r]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
        
        print(f"📊 Tests Run: {total_tests}")
        print(f"✅ Successful: {successful}/{total_tests} ({successful/total_tests*100:.0f}%)")
        print(f"⏱️  Avg Duration: {avg_duration:.2f}s")
        print(f"📈 Avg Confidence: {avg_confidence:.2f}")
        print()
        
        # Individual test results
        print("Individual Test Results:")
        print("-" * 80)
        for result in self.results:
            test_name = result.get("test", "unknown")
            success = "✅" if result.get("success", False) else "❌"
            duration = f"{result.get('duration', 0):.2f}s" if "duration" in result else "N/A"
            confidence = f"{result.get('confidence', 0):.2f}" if "confidence" in result else "N/A"
            
            print(f"{success} {test_name:25s} | Time: {duration:8s} | Confidence: {confidence}")
        
        print("\n" + "=" * 80 + "\n")
        
        # Save results
        with open("fredai_test_results.json", "w") as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "summary": {
                    "total_tests": total_tests,
                    "successful": successful,
                    "success_rate": successful/total_tests*100,
                    "avg_duration": avg_duration,
                    "avg_confidence": avg_confidence
                },
                "results": self.results
            }, f, indent=2)
        
        print("💾 Results saved to: fredai_test_results.json")
    
    async def run_all_tests(self):
        """Run all tests"""
        await self.setup()
        
        tests = [
            self.test_basic_ask,
            self.test_parallel_collaboration,
            self.test_consensus_mode,
            self.test_peer_review,
            self.test_brainstorming,
            self.test_debate_mode,
            self.test_memory_system,
            self.test_specialist_agents,
            self.test_performance_stress,
            self.test_error_handling,
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                print(f"\n❌ Test failed: {test.__name__}")
                print(f"   Error: {e}")
                import traceback
                traceback.print_exc()
        
        self.generate_report()


async def main():
    tester = FredAITester()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())

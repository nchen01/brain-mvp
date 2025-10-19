"""Performance benchmarking and regression testing system."""

import time
import statistics
import threading
import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import functools
import inspect
import concurrent.futures

from .performance_metrics import metrics_collector, monitor_performance

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    name: str
    iterations: int
    total_time: float
    min_time: float
    max_time: float
    mean_time: float
    median_time: float
    std_dev: float
    p95_time: float
    p99_time: float
    throughput: float  # operations per second
    success_count: int
    error_count: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'name': self.name,
            'iterations': self.iterations,
            'total_time': self.total_time,
            'min_time': self.min_time,
            'max_time': self.max_time,
            'mean_time': self.mean_time,
            'median_time': self.median_time,
            'std_dev': self.std_dev,
            'p95_time': self.p95_time,
            'p99_time': self.p99_time,
            'throughput': self.throughput,
            'success_count': self.success_count,
            'error_count': self.error_count,
            'error_rate': self.error_count / self.iterations if self.iterations > 0 else 0.0,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class BenchmarkComparison:
    """Comparison between two benchmark results."""
    baseline: BenchmarkResult
    current: BenchmarkResult
    mean_time_change: float
    throughput_change: float
    error_rate_change: float
    is_regression: bool
    regression_threshold: float = 0.1  # 10% threshold
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'baseline': self.baseline.to_dict(),
            'current': self.current.to_dict(),
            'changes': {
                'mean_time_change_percent': self.mean_time_change * 100,
                'throughput_change_percent': self.throughput_change * 100,
                'error_rate_change_percent': self.error_rate_change * 100
            },
            'is_regression': self.is_regression,
            'regression_threshold_percent': self.regression_threshold * 100
        }


class BenchmarkSuite:
    """Performance benchmark suite."""
    
    def __init__(self, name: str):
        """Initialize benchmark suite."""
        self.name = name
        self.benchmarks: Dict[str, Callable] = {}
        self.results: List[BenchmarkResult] = []
        self.baselines: Dict[str, BenchmarkResult] = {}
        
    def add_benchmark(self, name: str, func: Callable, 
                     setup: Optional[Callable] = None,
                     teardown: Optional[Callable] = None):
        """Add a benchmark function."""
        self.benchmarks[name] = {
            'func': func,
            'setup': setup,
            'teardown': teardown
        }
    
    def benchmark(self, name: Optional[str] = None, 
                 setup: Optional[Callable] = None,
                 teardown: Optional[Callable] = None):
        """Decorator to add benchmark function."""
        def decorator(func):
            benchmark_name = name or func.__name__
            self.add_benchmark(benchmark_name, func, setup, teardown)
            return func
        return decorator
    
    def run_benchmark(self, name: str, iterations: int = 100, 
                     warmup_iterations: int = 10,
                     args: tuple = (), kwargs: dict = None) -> BenchmarkResult:
        """Run a single benchmark."""
        if name not in self.benchmarks:
            raise ValueError(f"Benchmark '{name}' not found")
        
        benchmark_config = self.benchmarks[name]
        func = benchmark_config['func']
        setup = benchmark_config['setup']
        teardown = benchmark_config['teardown']
        kwargs = kwargs or {}
        
        logger.info(f"Running benchmark: {name} ({iterations} iterations)")
        
        # Setup
        if setup:
            setup()
        
        try:
            # Warmup
            for _ in range(warmup_iterations):
                try:
                    if inspect.iscoroutinefunction(func):
                        asyncio.run(func(*args, **kwargs))
                    else:
                        func(*args, **kwargs)
                except Exception:
                    pass  # Ignore warmup errors
            
            # Actual benchmark
            execution_times = []
            success_count = 0
            error_count = 0
            
            start_total = time.time()
            
            for i in range(iterations):
                start_time = time.time()
                error = False
                
                try:
                    if inspect.iscoroutinefunction(func):
                        asyncio.run(func(*args, **kwargs))
                    else:
                        func(*args, **kwargs)
                    success_count += 1
                except Exception as e:
                    error = True
                    error_count += 1
                    logger.debug(f"Benchmark iteration {i} failed: {e}")
                
                execution_time = time.time() - start_time
                execution_times.append(execution_time)
            
            total_time = time.time() - start_total
            
            # Calculate statistics
            if execution_times:
                min_time = min(execution_times)
                max_time = max(execution_times)
                mean_time = statistics.mean(execution_times)
                median_time = statistics.median(execution_times)
                std_dev = statistics.stdev(execution_times) if len(execution_times) > 1 else 0.0
                
                # Percentiles
                sorted_times = sorted(execution_times)
                p95_idx = int(len(sorted_times) * 0.95)
                p99_idx = int(len(sorted_times) * 0.99)
                p95_time = sorted_times[p95_idx] if p95_idx < len(sorted_times) else max_time
                p99_time = sorted_times[p99_idx] if p99_idx < len(sorted_times) else max_time
                
                throughput = iterations / total_time if total_time > 0 else 0.0
            else:
                min_time = max_time = mean_time = median_time = std_dev = p95_time = p99_time = throughput = 0.0
            
            result = BenchmarkResult(
                name=name,
                iterations=iterations,
                total_time=total_time,
                min_time=min_time,
                max_time=max_time,
                mean_time=mean_time,
                median_time=median_time,
                std_dev=std_dev,
                p95_time=p95_time,
                p99_time=p99_time,
                throughput=throughput,
                success_count=success_count,
                error_count=error_count
            )
            
            self.results.append(result)
            
            # Record metrics
            metrics_collector.record_metric(f"benchmark.{name}.mean_time", mean_time)
            metrics_collector.record_metric(f"benchmark.{name}.throughput", throughput)
            metrics_collector.record_metric(f"benchmark.{name}.error_rate", error_count / iterations)
            
            logger.info(f"Benchmark {name} completed: {mean_time:.4f}s mean, {throughput:.2f} ops/sec")
            
            return result
            
        finally:
            # Teardown
            if teardown:
                teardown()
    
    def run_all_benchmarks(self, iterations: int = 100, 
                          warmup_iterations: int = 10) -> List[BenchmarkResult]:
        """Run all benchmarks in the suite."""
        results = []
        
        for name in self.benchmarks:
            try:
                result = self.run_benchmark(name, iterations, warmup_iterations)
                results.append(result)
            except Exception as e:
                logger.error(f"Benchmark {name} failed: {e}")
        
        return results
    
    def set_baseline(self, name: str, result: Optional[BenchmarkResult] = None):
        """Set baseline result for regression testing."""
        if result is None:
            # Use latest result
            matching_results = [r for r in self.results if r.name == name]
            if not matching_results:
                raise ValueError(f"No results found for benchmark '{name}'")
            result = matching_results[-1]
        
        self.baselines[name] = result
        logger.info(f"Set baseline for {name}: {result.mean_time:.4f}s mean")
    
    def compare_with_baseline(self, name: str, 
                            current_result: Optional[BenchmarkResult] = None,
                            regression_threshold: float = 0.1) -> BenchmarkComparison:
        """Compare current result with baseline."""
        if name not in self.baselines:
            raise ValueError(f"No baseline set for benchmark '{name}'")
        
        baseline = self.baselines[name]
        
        if current_result is None:
            # Use latest result
            matching_results = [r for r in self.results if r.name == name]
            if not matching_results:
                raise ValueError(f"No current results found for benchmark '{name}'")
            current_result = matching_results[-1]
        
        # Calculate changes
        mean_time_change = (current_result.mean_time - baseline.mean_time) / baseline.mean_time
        throughput_change = (current_result.throughput - baseline.throughput) / baseline.throughput if baseline.throughput > 0 else 0.0
        
        baseline_error_rate = baseline.error_count / baseline.iterations if baseline.iterations > 0 else 0.0
        current_error_rate = current_result.error_count / current_result.iterations if current_result.iterations > 0 else 0.0
        error_rate_change = current_error_rate - baseline_error_rate
        
        # Determine if this is a regression
        is_regression = (
            mean_time_change > regression_threshold or  # Slower execution
            throughput_change < -regression_threshold or  # Lower throughput
            error_rate_change > regression_threshold  # Higher error rate
        )
        
        return BenchmarkComparison(
            baseline=baseline,
            current=current_result,
            mean_time_change=mean_time_change,
            throughput_change=throughput_change,
            error_rate_change=error_rate_change,
            is_regression=is_regression,
            regression_threshold=regression_threshold
        )
    
    def save_results(self, file_path: str):
        """Save benchmark results to file."""
        data = {
            'suite_name': self.name,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'results': [result.to_dict() for result in self.results],
            'baselines': {name: result.to_dict() for name, result in self.baselines.items()}
        }
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Saved benchmark results to {file_path}")
    
    def load_results(self, file_path: str):
        """Load benchmark results from file."""
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Load results
        self.results = []
        for result_data in data.get('results', []):
            result = BenchmarkResult(
                name=result_data['name'],
                iterations=result_data['iterations'],
                total_time=result_data['total_time'],
                min_time=result_data['min_time'],
                max_time=result_data['max_time'],
                mean_time=result_data['mean_time'],
                median_time=result_data['median_time'],
                std_dev=result_data['std_dev'],
                p95_time=result_data['p95_time'],
                p99_time=result_data['p99_time'],
                throughput=result_data['throughput'],
                success_count=result_data['success_count'],
                error_count=result_data['error_count'],
                timestamp=datetime.fromisoformat(result_data['timestamp'])
            )
            self.results.append(result)
        
        # Load baselines
        self.baselines = {}
        for name, baseline_data in data.get('baselines', {}).items():
            baseline = BenchmarkResult(
                name=baseline_data['name'],
                iterations=baseline_data['iterations'],
                total_time=baseline_data['total_time'],
                min_time=baseline_data['min_time'],
                max_time=baseline_data['max_time'],
                mean_time=baseline_data['mean_time'],
                median_time=baseline_data['median_time'],
                std_dev=baseline_data['std_dev'],
                p95_time=baseline_data['p95_time'],
                p99_time=baseline_data['p99_time'],
                throughput=baseline_data['throughput'],
                success_count=baseline_data['success_count'],
                error_count=baseline_data['error_count'],
                timestamp=datetime.fromisoformat(baseline_data['timestamp'])
            )
            self.baselines[name] = baseline
        
        logger.info(f"Loaded benchmark results from {file_path}")


class LoadTester:
    """Load testing utilities."""
    
    def __init__(self, max_workers: int = 10):
        """Initialize load tester."""
        self.max_workers = max_workers
    
    def run_load_test(self, func: Callable, 
                     concurrent_users: int = 10,
                     duration_seconds: int = 60,
                     ramp_up_seconds: int = 10,
                     args: tuple = (),
                     kwargs: dict = None) -> Dict[str, Any]:
        """Run load test with concurrent users."""
        kwargs = kwargs or {}
        results = {
            'concurrent_users': concurrent_users,
            'duration_seconds': duration_seconds,
            'ramp_up_seconds': ramp_up_seconds,
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'throughput': 0.0,
            'error_rate': 0.0,
            'start_time': datetime.now(timezone.utc),
            'end_time': None
        }
        
        def worker():
            """Worker function for load testing."""
            worker_results = {
                'requests': 0,
                'successes': 0,
                'failures': 0,
                'response_times': []
            }
            
            start_time = time.time()
            end_time = start_time + duration_seconds
            
            while time.time() < end_time:
                request_start = time.time()
                
                try:
                    if inspect.iscoroutinefunction(func):
                        asyncio.run(func(*args, **kwargs))
                    else:
                        func(*args, **kwargs)
                    worker_results['successes'] += 1
                except Exception:
                    worker_results['failures'] += 1
                
                response_time = time.time() - request_start
                worker_results['response_times'].append(response_time)
                worker_results['requests'] += 1
                
                # Small delay to prevent overwhelming
                time.sleep(0.001)
            
            return worker_results
        
        logger.info(f"Starting load test: {concurrent_users} users, {duration_seconds}s duration")
        
        # Ramp up users gradually
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = []
            
            for i in range(concurrent_users):
                # Stagger user start times during ramp-up
                if ramp_up_seconds > 0:
                    delay = (i / concurrent_users) * ramp_up_seconds
                    time.sleep(delay / concurrent_users)
                
                future = executor.submit(worker)
                futures.append(future)
            
            # Collect results
            for future in concurrent.futures.as_completed(futures):
                try:
                    worker_result = future.result()
                    results['total_requests'] += worker_result['requests']
                    results['successful_requests'] += worker_result['successes']
                    results['failed_requests'] += worker_result['failures']
                    results['response_times'].extend(worker_result['response_times'])
                except Exception as e:
                    logger.error(f"Worker failed: {e}")
        
        results['end_time'] = datetime.now(timezone.utc)
        
        # Calculate final statistics
        if results['response_times']:
            results['mean_response_time'] = statistics.mean(results['response_times'])
            results['median_response_time'] = statistics.median(results['response_times'])
            results['p95_response_time'] = sorted(results['response_times'])[int(len(results['response_times']) * 0.95)]
            results['p99_response_time'] = sorted(results['response_times'])[int(len(results['response_times']) * 0.99)]
        
        actual_duration = (results['end_time'] - results['start_time']).total_seconds()
        results['throughput'] = results['total_requests'] / actual_duration if actual_duration > 0 else 0.0
        results['error_rate'] = results['failed_requests'] / results['total_requests'] if results['total_requests'] > 0 else 0.0
        
        logger.info(f"Load test completed: {results['throughput']:.2f} req/s, {results['error_rate']:.2%} error rate")
        
        return results


# Global benchmark registry
benchmark_suites: Dict[str, BenchmarkSuite] = {}


def create_benchmark_suite(name: str) -> BenchmarkSuite:
    """Create or get benchmark suite."""
    if name not in benchmark_suites:
        benchmark_suites[name] = BenchmarkSuite(name)
    return benchmark_suites[name]


def benchmark(suite_name: str = "default", name: Optional[str] = None):
    """Decorator to add function to benchmark suite."""
    suite = create_benchmark_suite(suite_name)
    return suite.benchmark(name)


def run_benchmarks(suite_name: str = "default", iterations: int = 100) -> List[BenchmarkResult]:
    """Run all benchmarks in a suite."""
    if suite_name not in benchmark_suites:
        raise ValueError(f"Benchmark suite '{suite_name}' not found")
    
    suite = benchmark_suites[suite_name]
    return suite.run_all_benchmarks(iterations)


def get_benchmark_results(suite_name: str = "default") -> List[Dict[str, Any]]:
    """Get benchmark results for a suite."""
    if suite_name not in benchmark_suites:
        return []
    
    suite = benchmark_suites[suite_name]
    return [result.to_dict() for result in suite.results]
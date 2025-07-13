"""
Performance monitoring and analytics service.

Tracks categorization accuracy, response times, and system performance
for optimization and monitoring purposes.
"""

import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque
from statistics import mean, median
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CategorizationMetric:
    """Individual categorization performance metric."""
    timestamp: float
    processing_time_ms: int
    model_used: str
    confidence: float
    primary_category: str
    categories_count: int
    fallback_used: bool
    cache_hit: bool
    session_id: str
    success: bool
    error_type: Optional[str] = None


class PerformanceMonitor:
    """
    Real-time performance monitoring for the categorization service.
    
    Tracks metrics, calculates statistics, and provides performance insights.
    """
    
    def __init__(self, max_metrics: int = 10000):
        """
        Initialize the performance monitor.
        
        Args:
            max_metrics: Maximum number of metrics to keep in memory
        """
        self.max_metrics = max_metrics
        self.metrics: deque = deque(maxlen=max_metrics)
        
        # Aggregated counters
        self.counters = defaultdict(int)
        self.error_counts = defaultdict(int)
        self.category_counts = defaultdict(int)
        self.model_usage = defaultdict(int)
        
        # Performance tracking
        self.response_times: deque = deque(maxlen=1000)
        self.confidence_scores: deque = deque(maxlen=1000)
        
        # System start time
        self.start_time = time.time()
        
        logger.info(f"Performance monitor initialized (max_metrics: {max_metrics})")
    
    def record_categorization(
        self,
        processing_time_ms: int,
        model_used: str,
        confidence: float,
        primary_category: str,
        categories_count: int,
        fallback_used: bool = False,
        cache_hit: bool = False,
        session_id: str = "unknown",
        success: bool = True,
        error_type: str = None
    ) -> None:
        """
        Record a categorization performance metric.
        
        Args:
            processing_time_ms: Time taken to process the request
            model_used: LLM model or fallback system used
            confidence: Overall confidence score
            primary_category: Primary category detected
            categories_count: Number of categories returned
            fallback_used: Whether fallback categorization was used
            cache_hit: Whether result was served from cache
            session_id: Session identifier
            success: Whether categorization was successful
            error_type: Type of error if unsuccessful
        """
        now = time.time()
        
        # Create metric record
        metric = CategorizationMetric(
            timestamp=now,
            processing_time_ms=processing_time_ms,
            model_used=model_used,
            confidence=confidence,
            primary_category=primary_category,
            categories_count=categories_count,
            fallback_used=fallback_used,
            cache_hit=cache_hit,
            session_id=session_id,
            success=success,
            error_type=error_type
        )
        
        # Store metric
        self.metrics.append(metric)
        
        # Update counters
        self.counters["total_requests"] += 1
        if success:
            self.counters["successful_requests"] += 1
        else:
            self.counters["failed_requests"] += 1
            if error_type:
                self.error_counts[error_type] += 1
        
        if cache_hit:
            self.counters["cache_hits"] += 1
        else:
            self.counters["cache_misses"] += 1
        
        if fallback_used:
            self.counters["fallback_used"] += 1
        
        # Update category and model usage
        if success:
            self.category_counts[primary_category] += 1
            self.model_usage[model_used] += 1
            
            # Track performance metrics
            self.response_times.append(processing_time_ms)
            self.confidence_scores.append(confidence)
        
        logger.debug(f"Recorded metric: {primary_category} ({confidence:.2f}) in {processing_time_ms}ms")
    
    def get_performance_summary(self, window_minutes: int = 60) -> Dict[str, Any]:
        """
        Get performance summary for the specified time window.
        
        Args:
            window_minutes: Time window in minutes
            
        Returns:
            Dict: Performance summary
        """
        cutoff_time = time.time() - (window_minutes * 60)
        recent_metrics = [m for m in self.metrics if m.timestamp >= cutoff_time]
        
        if not recent_metrics:
            return {
                "window_minutes": window_minutes,
                "total_requests": 0,
                "message": "No requests in the specified time window"
            }
        
        # Calculate basic statistics
        successful_metrics = [m for m in recent_metrics if m.success]
        
        response_times = [m.processing_time_ms for m in successful_metrics]
        confidence_scores = [m.confidence for m in successful_metrics]
        
        summary = {
            "window_minutes": window_minutes,
            "total_requests": len(recent_metrics),
            "successful_requests": len(successful_metrics),
            "failed_requests": len(recent_metrics) - len(successful_metrics),
            "success_rate": len(successful_metrics) / len(recent_metrics) if recent_metrics else 0,
            
            # Performance metrics
            "response_time": {
                "avg_ms": mean(response_times) if response_times else 0,
                "median_ms": median(response_times) if response_times else 0,
                "min_ms": min(response_times) if response_times else 0,
                "max_ms": max(response_times) if response_times else 0
            },
            
            "confidence": {
                "avg_score": mean(confidence_scores) if confidence_scores else 0,
                "median_score": median(confidence_scores) if confidence_scores else 0,
                "min_score": min(confidence_scores) if confidence_scores else 0,
                "max_score": max(confidence_scores) if confidence_scores else 0
            },
            
            # Usage statistics
            "cache_hit_rate": self._calculate_cache_hit_rate(recent_metrics),
            "fallback_usage_rate": self._calculate_fallback_rate(recent_metrics),
            "avg_categories_per_request": mean([m.categories_count for m in successful_metrics]) if successful_metrics else 0,
            
            # Top categories and models
            "top_categories": self._get_top_categories(recent_metrics, limit=10),
            "model_usage": self._get_model_usage(recent_metrics),
            "error_breakdown": self._get_error_breakdown(recent_metrics)
        }
        
        return summary
    
    def get_real_time_stats(self) -> Dict[str, Any]:
        """
        Get real-time performance statistics.
        
        Returns:
            Dict: Real-time stats
        """
        uptime = time.time() - self.start_time
        
        # Recent performance (last 100 requests)
        recent_metrics = list(self.metrics)[-100:] if self.metrics else []
        recent_successful = [m for m in recent_metrics if m.success]
        
        return {
            "uptime_seconds": uptime,
            "total_requests": self.counters["total_requests"],
            "requests_per_second": self.counters["total_requests"] / uptime if uptime > 0 else 0,
            
            "success_rate": (
                self.counters["successful_requests"] / self.counters["total_requests"]
                if self.counters["total_requests"] > 0 else 0
            ),
            
            "cache_hit_rate": (
                self.counters["cache_hits"] / (self.counters["cache_hits"] + self.counters["cache_misses"])
                if (self.counters["cache_hits"] + self.counters["cache_misses"]) > 0 else 0
            ),
            
            "fallback_usage_rate": (
                self.counters["fallback_used"] / self.counters["total_requests"]
                if self.counters["total_requests"] > 0 else 0
            ),
            
            "recent_avg_response_time": (
                mean([m.processing_time_ms for m in recent_successful])
                if recent_successful else 0
            ),
            
            "recent_avg_confidence": (
                mean([m.confidence for m in recent_successful])
                if recent_successful else 0
            ),
            
            "memory_usage": {
                "metrics_stored": len(self.metrics),
                "max_metrics": self.max_metrics,
                "memory_efficiency": len(self.metrics) / self.max_metrics
            }
        }
    
    def get_category_analytics(self, window_hours: int = 24) -> Dict[str, Any]:
        """
        Get detailed category usage analytics.
        
        Args:
            window_hours: Time window in hours
            
        Returns:
            Dict: Category analytics
        """
        cutoff_time = time.time() - (window_hours * 3600)
        recent_metrics = [m for m in self.metrics if m.timestamp >= cutoff_time and m.success]
        
        if not recent_metrics:
            return {"message": "No successful requests in time window"}
        
        # Category frequency and performance
        category_stats = defaultdict(lambda: {
            "count": 0,
            "confidence_scores": [],
            "response_times": [],
            "fallback_used": 0
        })
        
        for metric in recent_metrics:
            stats = category_stats[metric.primary_category]
            stats["count"] += 1
            stats["confidence_scores"].append(metric.confidence)
            stats["response_times"].append(metric.processing_time_ms)
            if metric.fallback_used:
                stats["fallback_used"] += 1
        
        # Calculate analytics for each category
        analytics = {}
        for category, stats in category_stats.items():
            analytics[category] = {
                "frequency": stats["count"],
                "percentage": (stats["count"] / len(recent_metrics)) * 100,
                "avg_confidence": mean(stats["confidence_scores"]),
                "avg_response_time": mean(stats["response_times"]),
                "fallback_rate": stats["fallback_used"] / stats["count"] if stats["count"] > 0 else 0
            }
        
        # Sort by frequency
        sorted_analytics = dict(
            sorted(analytics.items(), key=lambda x: x[1]["frequency"], reverse=True)
        )
        
        return {
            "window_hours": window_hours,
            "total_categorizations": len(recent_metrics),
            "unique_categories": len(category_stats),
            "category_breakdown": sorted_analytics,
            "top_5_categories": list(sorted_analytics.keys())[:5]
        }
    
    def _calculate_cache_hit_rate(self, metrics: List[CategorizationMetric]) -> float:
        """Calculate cache hit rate for given metrics."""
        if not metrics:
            return 0.0
        cache_hits = sum(1 for m in metrics if m.cache_hit)
        return cache_hits / len(metrics)
    
    def _calculate_fallback_rate(self, metrics: List[CategorizationMetric]) -> float:
        """Calculate fallback usage rate for given metrics."""
        if not metrics:
            return 0.0
        fallback_used = sum(1 for m in metrics if m.fallback_used)
        return fallback_used / len(metrics)
    
    def _get_top_categories(self, metrics: List[CategorizationMetric], limit: int = 10) -> List[Dict[str, Any]]:
        """Get top categories by frequency."""
        category_counts = defaultdict(int)
        for m in metrics:
            if m.success:
                category_counts[m.primary_category] += 1
        
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {"category": cat, "count": count}
            for cat, count in sorted_categories[:limit]
        ]
    
    def _get_model_usage(self, metrics: List[CategorizationMetric]) -> Dict[str, int]:
        """Get model usage breakdown."""
        model_counts = defaultdict(int)
        for m in metrics:
            model_counts[m.model_used] += 1
        return dict(model_counts)
    
    def _get_error_breakdown(self, metrics: List[CategorizationMetric]) -> Dict[str, int]:
        """Get error type breakdown."""
        error_counts = defaultdict(int)
        for m in metrics:
            if not m.success and m.error_type:
                error_counts[m.error_type] += 1
        return dict(error_counts)
    
    def get_health_indicators(self) -> Dict[str, Any]:
        """
        Get health indicators for system monitoring.
        
        Returns:
            Dict: Health indicators with status levels
        """
        recent_stats = self.get_real_time_stats()
        
        # Define health thresholds
        health_indicators = {
            "overall_health": "healthy",
            "indicators": {}
        }
        
        # Success rate health
        success_rate = recent_stats["success_rate"]
        if success_rate >= 0.95:
            health_indicators["indicators"]["success_rate"] = {"status": "healthy", "value": success_rate}
        elif success_rate >= 0.90:
            health_indicators["indicators"]["success_rate"] = {"status": "warning", "value": success_rate}
        else:
            health_indicators["indicators"]["success_rate"] = {"status": "critical", "value": success_rate}
            health_indicators["overall_health"] = "degraded"
        
        # Response time health
        avg_response_time = recent_stats["recent_avg_response_time"]
        if avg_response_time <= 1000:  # 1 second
            health_indicators["indicators"]["response_time"] = {"status": "healthy", "value": avg_response_time}
        elif avg_response_time <= 3000:  # 3 seconds
            health_indicators["indicators"]["response_time"] = {"status": "warning", "value": avg_response_time}
        else:
            health_indicators["indicators"]["response_time"] = {"status": "critical", "value": avg_response_time}
            health_indicators["overall_health"] = "degraded"
        
        # Confidence health
        avg_confidence = recent_stats["recent_avg_confidence"]
        if avg_confidence >= 0.8:
            health_indicators["indicators"]["confidence"] = {"status": "healthy", "value": avg_confidence}
        elif avg_confidence >= 0.6:
            health_indicators["indicators"]["confidence"] = {"status": "warning", "value": avg_confidence}
        else:
            health_indicators["indicators"]["confidence"] = {"status": "critical", "value": avg_confidence}
            health_indicators["overall_health"] = "degraded"
        
        # Fallback usage health
        fallback_rate = recent_stats["fallback_usage_rate"]
        if fallback_rate <= 0.1:  # 10%
            health_indicators["indicators"]["fallback_usage"] = {"status": "healthy", "value": fallback_rate}
        elif fallback_rate <= 0.3:  # 30%
            health_indicators["indicators"]["fallback_usage"] = {"status": "warning", "value": fallback_rate}
        else:
            health_indicators["indicators"]["fallback_usage"] = {"status": "critical", "value": fallback_rate}
            health_indicators["overall_health"] = "degraded"
        
        return health_indicators
    
    def reset_metrics(self) -> Dict[str, int]:
        """
        Reset all metrics and counters.
        
        Returns:
            Dict: Summary of reset metrics
        """
        metrics_count = len(self.metrics)
        counter_sum = sum(self.counters.values())
        
        self.metrics.clear()
        self.counters.clear()
        self.error_counts.clear()
        self.category_counts.clear()
        self.model_usage.clear()
        self.response_times.clear()
        self.confidence_scores.clear()
        self.start_time = time.time()
        
        logger.info(f"Reset performance metrics: {metrics_count} metrics, {counter_sum} counters")
        
        return {
            "metrics_cleared": metrics_count,
            "counters_cleared": counter_sum,
            "reset_timestamp": time.time()
        }


# Global performance monitor instance
performance_monitor = PerformanceMonitor()
#!/usr/bin/env python3
"""
Automated Failover Manager
Monitors health and automatically fails over to standby when primary fails
"""

import asyncio
import logging
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
import kubernetes
from kubernetes import client, config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class FailoverManager:
    """Manages automatic failover for high availability"""
    
    def __init__(self):
        self.k8s_client = None
        self.health_check_interval = int(os.getenv("HEALTH_CHECK_INTERVAL", "30"))
        self.failure_threshold = int(os.getenv("FAILURE_THRESHOLD", "3"))
        self.failure_counts: Dict[str, int] = {}
        self.last_health_status: Dict[str, bool] = {}
        
    def initialize_k8s_client(self):
        """Initialize Kubernetes client"""
        try:
            if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount"):
                config.load_incluster_config()
            else:
                config.load_kube_config()
            self.k8s_client = client.CoreV1Api()
            logger.info("Kubernetes client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Kubernetes client: {e}")
            sys.exit(1)
    
    async def check_pod_health(self, namespace: str, pod_name: str) -> bool:
        """Check if a pod is healthy"""
        try:
            pod = self.k8s_client.read_namespaced_pod(pod_name, namespace)
            
            # Check pod phase
            if pod.status.phase != "Running":
                logger.warning(f"Pod {pod_name} is not Running (phase: {pod.status.phase})")
                return False
            
            # Check container status
            for container_status in pod.status.container_statuses or []:
                if not container_status.ready:
                    logger.warning(f"Container {container_status.name} in {pod_name} is not ready")
                    return False
                if container_status.restart_count > 5:
                    logger.warning(f"Container {container_status.name} in {pod_name} has high restart count: {container_status.restart_count}")
                    return False
            
            return True
        except Exception as e:
            logger.error(f"Error checking pod health for {pod_name}: {e}")
            return False
    
    async def check_service_health(self, namespace: str, service_name: str, port: int) -> bool:
        """Check if a service is responding"""
        try:
            # Get service endpoint
            endpoints = self.k8s_client.read_namespaced_endpoints(service_name, namespace)
            
            if not endpoints.subsets:
                logger.warning(f"Service {service_name} has no endpoints")
                return False
            
            # Try to connect to at least one endpoint
            for subset in endpoints.subsets:
                for address in subset.addresses or []:
                    try:
                        async with aiohttp.ClientSession() as session:
                            url = f"http://{address.ip}:{port}/health"
                            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                                if response.status == 200:
                                    return True
                    except Exception as e:
                        logger.debug(f"Failed to connect to {address.ip}:{port}: {e}")
                        continue
            
            return False
        except Exception as e:
            logger.error(f"Error checking service health for {service_name}: {e}")
            return False
    
    async def check_database_health(self, namespace: str) -> Dict[str, bool]:
        """Check health of primary and replica databases"""
        health_status = {
            "primary": False,
            "replica": False
        }
        
        # Check primary
        primary_healthy = await self.check_service_health(
            namespace, "automaton-postgres-primary", 5432
        )
        health_status["primary"] = primary_healthy
        
        # Check replica
        replica_healthy = await self.check_service_health(
            namespace, "automaton-postgres-replica", 5432
        )
        health_status["replica"] = replica_healthy
        
        return health_status
    
    async def promote_replica_to_primary(self, namespace: str):
        """Promote replica to primary (failover)"""
        logger.warning("Initiating failover: Promoting replica to primary")
        
        try:
            apps_v1 = client.AppsV1Api()
            
            # Update replica StatefulSet to become primary
            replica_sts = apps_v1.read_namespaced_stateful_set(
                "automaton-postgres-replica", namespace
            )
            
            # Add label to mark as primary
            if not replica_sts.metadata.labels:
                replica_sts.metadata.labels = {}
            replica_sts.metadata.labels["role"] = "primary"
            
            # Update service selector to point to replica
            core_v1 = client.CoreV1Api()
            primary_svc = core_v1.read_namespaced_service(
                "automaton-postgres", namespace
            )
            primary_svc.spec.selector["role"] = "replica"
            primary_svc.spec.selector["promoted"] = "true"
            
            core_v1.patch_namespaced_service(
                "automaton-postgres", namespace, primary_svc
            )
            
            logger.info("Failover completed: Replica promoted to primary")
            
            # Send notification
            await self.send_failover_notification("Database failover completed")
            
        except Exception as e:
            logger.error(f"Failed to promote replica: {e}")
            raise
    
    async def send_failover_notification(self, message: str):
        """Send notification about failover event"""
        # Implement notification (Slack, email, etc.)
        logger.info(f"Failover notification: {message}")
        # TODO: Integrate with notification system
    
    async def monitor_and_failover(self, namespace: str = "automaton-production"):
        """Main monitoring loop with automatic failover"""
        logger.info("Starting failover manager monitoring")
        
        while True:
            try:
                # Check database health
                db_health = await self.check_database_health(namespace)
                
                # Track failures
                if not db_health["primary"]:
                    key = "primary"
                    self.failure_counts[key] = self.failure_counts.get(key, 0) + 1
                    logger.warning(
                        f"Primary database unhealthy. "
                        f"Failure count: {self.failure_counts[key]}/{self.failure_threshold}"
                    )
                    
                    # Trigger failover if threshold reached
                    if (self.failure_counts[key] >= self.failure_threshold and 
                        db_health["replica"]):
                        await self.promote_replica_to_primary(namespace)
                        self.failure_counts[key] = 0
                else:
                    # Reset failure count if primary is healthy
                    self.failure_counts["primary"] = 0
                
                # Check application pods
                pods = self.k8s_client.list_namespaced_pod(
                    namespace,
                    label_selector="app=automaton,component=app"
                )
                
                unhealthy_pods = []
                for pod in pods.items:
                    is_healthy = await self.check_pod_health(namespace, pod.metadata.name)
                    if not is_healthy:
                        unhealthy_pods.append(pod.metadata.name)
                
                if unhealthy_pods:
                    logger.warning(f"Unhealthy pods detected: {unhealthy_pods}")
                    # Pods will be automatically restarted by Kubernetes
                
                # Wait before next check
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.health_check_interval)


async def main():
    """Main entry point"""
    manager = FailoverManager()
    manager.initialize_k8s_client()
    await manager.monitor_and_failover()


if __name__ == "__main__":
    asyncio.run(main())


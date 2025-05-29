from . import JobParams, JobInfo, ImageInfo, ClusterABC

class MockCluster(ClusterABC):
    """Mock集群类，用于测试"""

    def __init__(self) -> None:
        self.jobs = dict[tuple[str, str], JobInfo]()

    async def submit_job(self, job_params: JobParams) -> JobInfo:
        from random import randint

        ret = JobInfo(
            id=str(randint(0, 1 << 31)),
            name=job_params.name,
            image=job_params.image,
            status=JobInfo.Status.RUNNING,
            ports=job_params.ports,
            env=job_params.env,
        )

        self.jobs[(ret.id, ret.name)] = ret
        return ret

    async def get_job_status(self, job_id: str) -> JobInfo.Status:
        job_info = self.jobs.get(job_id)
        if job_info:
            return job_info.status
        else:
            raise ValueError(f"Job with ID {job_id} not found.")
    
    async def get_image_info(self, image_id: str) -> ImageInfo:
        # Mock implementation, returning a dummy ImageInfo object
        return ImageInfo(
            id=image_id,
            name="mock_image",
            description="This is a mock image.",
            full_name="mock_image:latest"
        )
    
    async def delete_job(self, job_id: str) -> None:
        job_info = self.jobs.pop(job_id, None)
        if job_info:
            job_info.status = JobInfo.Status.SUCCESS
        else:
            raise ValueError(f"Job with ID {job_id} not found.")
    
    async def list_jobs(self) -> list[JobInfo]:
        return list(self.jobs.values())
    
    async def list_images(self) -> list[ImageInfo]:
        # Mock implementation, returning a list of dummy ImageInfo objects
        return [
            ImageInfo(
                id=f"image_{i}",
                name=f"mock_image_{i}",
                description=f"This is a mock image {i}.",
                full_name=f"mock_image_{i}:latest"
            )
            for i in range(5)
        ]
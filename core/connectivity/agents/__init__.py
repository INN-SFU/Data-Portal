from .s3_agent import S3StorageAgent
from .posix_agent import PosixStorageAgent

available_flavours = {
    S3StorageAgent.FLAVOUR: S3StorageAgent,
    PosixStorageAgent.FLAVOUR: PosixStorageAgent
}

from .s3_agent import S3Agent
from .posix_agent import PosixAgent

available_flavours = {
    S3Agent.FLAVOUR: S3Agent,
    PosixAgent.FLAVOUR: PosixAgent
}

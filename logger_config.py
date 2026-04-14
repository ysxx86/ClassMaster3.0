import logging

def setup_logger():
    """配置日志"""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler("logs/root_server.log"),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

import logging
import re

class TokenFilter(logging.Filter):
    def __init__(self, token):
        super().__init__()
        self.token = token
        self.token_pattern = re.compile(re.escape(token))

    def filter(self, record):
        
        if isinstance(record.msg, str):
            record.msg = self.token_pattern.sub('***', record.msg)
        
        if isinstance(record.args, tuple):
            record.args = tuple(
                self.token_pattern.sub('***', str(arg)) if isinstance(arg, str) else arg
                for arg in record.args
            )
       
        if hasattr(record, 'extra'):
            for key, value in record.extra.items():
                if isinstance(value, str):
                    record.extra[key] = self.token_pattern.sub('***', value)
        
        if hasattr(record, 'pathname') and isinstance(record.pathname, str):
            record.pathname = self.token_pattern.sub('***', record.pathname)
        if hasattr(record, 'funcName') and isinstance(record.funcName, str):
            record.funcName = self.token_pattern.sub('***', record.funcName)
        return True

def setup_logging(token):
    
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
  
    file_handler = logging.FileHandler('bot.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    file_handler.addFilter(TokenFilter(token))
    logger.addHandler(file_handler)

    
    httpx_logger = logging.getLogger('httpx')
    httpx_logger.setLevel(logging.INFO)
    httpx_logger.handlers = []
    httpx_logger.addHandler(file_handler)
    httpx_logger.propagate = False
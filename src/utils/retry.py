"""
重试机制工具模块
提供统一的请求重试装饰器
"""
import time
import logging
import functools
from typing import Callable, TypeVar, Type, Tuple, Optional
import requests

logger = logging.getLogger(__name__)

T = TypeVar('T')


class RetryExhausted(Exception):
    """重试次数耗尽"""
    pass


def retry(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    exponential_backoff: bool = True,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int, int], None]] = None
):
    """
    重试装饰器
    
    Args:
        max_retries: 最大重试次数
        retry_delay: 初始重试延迟（秒）
        exponential_backoff: 是否使用指数退避
        exceptions: 需要重试的异常类型
        on_retry: 重试时的回调函数
    
    Returns:
        装饰后的函数
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        if exponential_backoff:
                            delay = retry_delay * (2 ** attempt)
                        else:
                            delay = retry_delay
                        
                        logger.warning(
                            f"Retry {attempt + 1}/{max_retries} for {func.__name__}: {e}. "
                            f"Waiting {delay:.1f}s..."
                        )
                        
                        if on_retry:
                            try:
                                on_retry(e, attempt + 1, max_retries)
                            except Exception as callback_error:
                                logger.error(f"Retry callback error: {callback_error}")
                        
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries} retries exhausted for {func.__name__}"
                        )
            
            raise RetryExhausted(
                f"Function {func.__name__} failed after {max_retries} retries"
            ) from last_exception
        
        return wrapper
    return decorator


class RetryableRequest:
    """可重试的 HTTP 请求封装"""
    
    def __init__(
        self,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 30.0,
        retry_status_codes: Tuple[int, ...] = (500, 502, 503, 504)
    ):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout
        self.retry_status_codes = retry_status_codes
    
    def get(self, url: str, **kwargs) -> requests.Response:
        """GET 请求 with retry"""
        return self._request("GET", url, **kwargs)
    
    def post(self, url: str, **kwargs) -> requests.Response:
        """POST 请求 with retry"""
        return self._request("POST", url, **kwargs)
    
    def _request(self, method: str, url: str, **kwargs) -> requests.Response:
        """执行请求 with retry"""
        kwargs.setdefault("timeout", self.timeout)
        last_exception = None
        last_response = None
        
        for attempt in range(self.max_retries + 1):
            try:
                if method == "GET":
                    response = requests.get(url, **kwargs)
                else:
                    response = requests.post(url, **kwargs)
                
                if response.status_code in self.retry_status_codes:
                    if attempt < self.max_retries:
                        delay = self.retry_delay * (2 ** attempt)
                        logger.warning(
                            f"Request to {url} returned {response.status_code}, "
                            f"retrying in {delay:.1f}s..."
                        )
                        time.sleep(delay)
                        last_response = response
                        continue
                    return response
                
                return response
            
            except requests.exceptions.RequestException as e:
                last_exception = e
                if attempt < self.max_retries:
                    delay = self.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"Request to {url} failed: {e}, retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
        
        if last_response:
            return last_response
        if last_exception:
            raise last_exception
        
        raise requests.exceptions.RequestError(f"All retries exhausted for {url}")


def create_retryable_client(
    max_retries: int = 3,
    retry_delay: float = 1.0,
    timeout: float = 30.0
) -> RetryableRequest:
    """创建可重试的 HTTP 客户端"""
    return RetryableRequest(
        max_retries=max_retries,
        retry_delay=retry_delay,
        timeout=timeout
    )
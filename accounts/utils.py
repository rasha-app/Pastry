import secrets,time,logging
from django.conf import settings
from django.core.cache import cache
from django.utils.translation import gettext_lazy as _

from .adapters import send_sms_ir

logger = logging.getLogger(__name__)

def send_otp_to_phone(phone,suffix):
    CACHE_TIME = getattr(settings,'PHONE_VERIFY_CODE_TTL',120)
    code = secrets.randbelow(900000) + 100000
    
    if settings.DEBUG:
        print('\n','-'*10,code,'-'*10,'\n')
    response_json = send_sms_ir(phone,code)
    if response_json.get('status') == 1:
        expire_at = time.time() + CACHE_TIME
        key = f"{phone}{suffix}"
        value = {"code": code,'expire': expire_at,"attempts": 0,}
        cache.set(key, value, CACHE_TIME)
        
        return {'status':1,'msg':_('One-time password has been sent, please check your inbox.')}
    
    elif response_json.get('status') == 9:
        return {'status': 0, 'msg': _('SMS service is temporarily unavailable.')}
    
    else:
        return {'status': 2, 'msg': _('Unspecified error, try again later.')}

def get_cached_otp(phone, suffix):
    try:
        data = cache.get(f'{phone}{suffix}')
        if data is None:
            return None
        # اعتبارسنجی ساختار داده
        if not isinstance(data, dict) or 'code' not in data or 'expire' not in data:
            cache.delete(f'{phone}{suffix}')
            return None
        return data
    except Exception as e:
        logger.exception(msg=f'An unexpected error occurred in function <get_cached_otp>: {e}')
        return None
    
def clear_otp(phone, suffix):
    try:
        key = f'{phone}{suffix}'
        cache.delete(key)
        return True
    except Exception as e:
        logger.exception(msg=f'An unexpected error occurred in function <clear_otp>: {e}')
        return False

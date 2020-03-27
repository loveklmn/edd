
import requests
appid = 'wxe35e744aac84b5ee'
secret = '27c28f20b36af5a623ec1ca6d2171e17'
grant_type = 'authorization_code'
baseUrl = 'https://api.weixin.qq.com/sns/jscode2session'


def get_open_id(js_code):
    '''
    correct response
    {"session_key":"TLLhUtITOfxo5idQEZ61jA==","openid":"oSNkC5ag6hpZQJMdi08f_BUNTq7k"}
    error response
    {"errcode":40029,"errmsg":"invalid code, hints: [ req_id: Ganbm24ce-wkoqcA ]"}
    '''
    ret = requests.get(
        f'baseUrl?appid={appid}&secret={secret}&js_code={js_code}&grant_type={grant_type}').text

    if ret.get('openid'):
        return {'openid': ret.openid}
    else:
        raise Exception(ret.errmsg)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# @FileName：     utils.py
# @Software:      
# @Author:         Leven Xiang
# @Mail:           xiangle0109@outlook.com
# @Date：          2021/5/20 8:47

from django.shortcuts import render
from django.http import HttpResponseRedirect
import logging
from utils.crypto import Crypto
from pwdselfservice.local_settings import TMPID_COOKIE_AGE
from django.conf import settings
from pwdselfservice import crypto_key

logger = logging.getLogger('django')


def code_2_user_id(ops, request, msg_template, home_url, code):
    _status, user_id = ops.get_user_id_by_code(code)
    # 判断 user_id 在本企业钉钉/微信中是否存在
    if not _status:
        context = {
            'msg': '获取钉钉userid失败，错误信息：{}'.format(user_id),
            'button_click': "window.location.href='%s'" % home_url,
            'button_display': "返回主页"
        }
        return render(request, msg_template, context)
    detail_status, user_info = ops.get_user_detail_by_user_id(user_id)
    if not detail_status:
        context = {
            'msg': '获取钉钉用户信息失败，错误信息：{}'.format(user_info),
            'button_click': "window.location.href='%s'" % home_url,
            'button_display': "返回主页"
        }
        return render(request, msg_template, context)
    return user_id, user_info


def crypto_id_2_user_info(ops, request, msg_template, home_url, scan_app_tag):
    try:
        crypto_tmp_id = request.COOKIES.get('tmpid')
    except Exception as e:
        crypto_tmp_id = None
        logger.error('[异常] ：%s' % str(e))
    if not crypto_tmp_id:
        logger.error('[异常]  请求方法：%s，请求路径：%s，未能拿到TmpID或会话己超时。' % (request.method, request.path))
        context = {
            'msg': "会话己超时，请重新扫码验证用户信息。",
            'button_click': "window.location.href='%s'" % home_url,
            'button_display': "返回主页"
        }
        return render(request, msg_template, context)
    # 解密
    crypto = Crypto(crypto_key)
    user_id = crypto.decrypt(crypto_tmp_id)
    # 通过user_id拿到用户的邮箱，并格式化为username
    userid_status, user_info = ops.get_user_detail_by_user_id(user_id)
    if not userid_status:
        context = {
            'msg': '获取{}用户信息失败，错误信息：{}'.format(user_info, scan_app_tag),
            'button_click': "window.location.href='%s'" % home_url,
            'button_display': "返回主页"
        }
        return render(request, msg_template, context)

    return user_info


def crypto_user_id_2_cookie(user_id):
    crypto = Crypto(crypto_key)
    # 对user_id进行加密，因为user_id基本上固定不变的，为了防止user_id泄露而导致重复使用，进行加密后再传回。
    _id_cryto = crypto.encrypt(user_id)
    # 配置cookie，通过cookie把加密后的用户user_id传到重置密码页面，并重定向到重置密码页面。
    set_cookie = HttpResponseRedirect('resetPassword')
    set_cookie.set_cookie('tmpid', _id_cryto, expires=TMPID_COOKIE_AGE)
    return set_cookie


def crypto_id_2_user_id(request, msg_template, home_url):
    try:
        crypto_tmp_id = request.COOKIES.get('tmpid')
    except Exception as e:
        logger.error('[异常] ：%s' % str(e))
        logger.error('[异常]  请求方法：%s，请求路径：%s，未能拿到TmpID或会话己超时。' % (request.method, request.path))
        context = {
            'msg': "会话己超时，请重新扫码验证用户信息。",
            'button_click': "window.location.href='%s'" % home_url,
            'button_display': "返回主页"
        }
        return render(request, msg_template, context)
    # 解密
    crypto = Crypto(crypto_key)
    return crypto.decrypt(crypto_tmp_id)


def ops_account(ad_ops, request, msg_template, home_url, username, new_password):
    if ad_ops.ad_ensure_user_by_account(username) is False:
        context = {
            'msg': "账号[%s]在AD中不存在，请确认当前钉钉扫码账号绑定的邮箱是否和您正在使用的邮箱一致？或者该账号己被禁用！\n猜测：您的账号或邮箱是否是带有数字或其它字母区分？" % username,
            'button_click': "window.location.href='%s'" % home_url,
            'button_display': "返回主页"
        }
        return render(request, msg_template, context)

    account_code = ad_ops.ad_get_user_status_by_account(username)
    if account_code in settings.AD_ACCOUNT_DISABLE_CODE:
        context = {
            'msg': "此账号状态为己禁用，请联系HR确认账号是否正确。",
            'button_click': "window.location.href='%s'" % home_url,
            'button_display': "返回主页"
        }
        return render(request, msg_template, context)
    if new_password:
        reset_status, result = ad_ops.ad_reset_user_pwd_by_account(username=username, new_password=new_password)
        if reset_status:
            # 重置密码并执行一次解锁，防止重置后账号还是锁定状态。
            unlock_status, result = ad_ops.ad_unlock_user_by_account(username)
            if unlock_status:
                context = {
                    'msg': "密码己修改/重置成功，请妥善保管。你可以点击返回主页或直接关闭此页面！",
                    'button_click': "window.location.href='%s'" % home_url,
                    'button_display': "返回主页"
                }
                return render(request, msg_template, context)
        else:
            context = {
                'msg': "密码未修改/重置成功，错误信息：{}".format(result),
                'button_click': "window.location.href='%s'" % home_url,
                'button_display': "返回主页"
            }
            return render(request, msg_template, context)
    else:
        unlock_status, result = ad_ops.ad_unlock_user_by_account(username)
        if unlock_status:
            context = {
                'msg': "账号己解锁成功。你可以点击返回主页或直接关闭此页面！",
                'button_click': "window.location.href='%s'" % home_url,
                'button_display': "返回主页"
            }
            return render(request, msg_template, context)
        else:
            context = {
                'msg': "账号未能解锁，错误信息：{}".format(result),
                'button_click': "window.location.href='%s'" % home_url,
                'button_display': "返回主页"
            }
            return render(request, msg_template, context)

# GNU MediaGoblin -- federated, autonomous media hosting
# Copyright (C) 2011, 2012 MediaGoblin contributors.  See AUTHORS.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
import uuid
import datetime

import forms as auth_forms
from mediagoblin.tools.response import render_to_response, redirect, render_404
from mediagoblin.db.models import User
from mediagoblin.tools.translate import pass_to_ugettext as _
from mediagoblin import messages
from mediagoblin.auth.views import email_debug_message
from mediagoblin.auth.lib import send_fp_verification_email
from mediagoblin.auth import lib as auth_lib



def forgot_password(request):
    """
    Forgot password view

    Sends an email with an url to renew forgotten password.
    Use GET querystring parameter 'username' to pre-populate the input field
    """
    fp_form = auth_forms.ForgotPassForm(request.form,
                                        username=request.args.get('username'))

    if not (request.method == 'POST' and fp_form.validate()):
        # Either GET request, or invalid form submitted. Display the template
        return render_to_response(request,
            'mediagoblin/plugins/basic_auth/forgot_password.html', {'fp_form': fp_form})

    # If we are here: method == POST and form is valid. username casing
    # has been sanitized. Store if a user was found by email. We should
    # not reveal if the operation was successful then as we don't want to
    # leak if an email address exists in the system.
    found_by_email = '@' in fp_form.username.data

    if found_by_email:
        user = User.query.filter_by(
            email=fp_form.username.data).first()
        # Don't reveal success in case the lookup happened by email address.
        success_message = _("If that email address (case sensitive!) is "
                            "registered an email has been sent with "
                            "instructions on how to change your password.")

    else:  # found by username
        user = User.query.filter_by(
            username=fp_form.username.data).first()

        if user is None:
            messages.add_message(request,
                                 messages.WARNING,
                                 _("Couldn't find someone with that username."))
            return redirect(request, 'mediagoblin.auth.forgot_password')

        success_message = _("An email has been sent with instructions "
                            "on how to change your password.")

    if user and not(user.email_verified and user.status == 'active'):
        # Don't send reminder because user is inactive or has no verified email
        messages.add_message(request,
            messages.WARNING,
            _("Could not send password recovery email as your username is in"
              "active or your account's email address has not been verified."))

        return redirect(request, 'mediagoblin.user_pages.user_home',
                        user=user.username)

    # SUCCESS. Send reminder and return to login page
    if user:
        user.fp_verification_key = unicode(uuid.uuid4())
        user.fp_token_expire = datetime.datetime.now() + \
                               datetime.timedelta(days=10)
        user.save()

        email_debug_message(request)
        send_fp_verification_email(user, request)

    messages.add_message(request, messages.INFO, success_message)
    return redirect(request, 'mediagoblin.auth.login')


def verify_forgot_password(request):
    """
    Check the forgot-password verification and possibly let the user
    change their password because of it.
    """
    # get form data variables, and specifically check for presence of token
    formdata = _process_for_token(request)
    if not formdata['has_userid_and_token']:
        return render_404(request)

    formdata_token = formdata['vars']['token']
    formdata_userid = formdata['vars']['userid']
    formdata_vars = formdata['vars']

    # check if it's a valid user id
    user = User.query.filter_by(id=formdata_userid).first()
    if not user:
        return render_404(request)

    # check if we have a real user and correct token
    if ((user and user.fp_verification_key and
         user.fp_verification_key == unicode(formdata_token) and
         datetime.datetime.now() < user.fp_token_expire
         and user.email_verified and user.status == 'active')):

        cp_form = auth_forms.ChangePassForm(formdata_vars)

        if request.method == 'POST' and cp_form.validate():
            user.pw_hash = auth_lib.bcrypt_gen_password_hash(
                cp_form.password.data)
            user.fp_verification_key = None
            user.fp_token_expire = None
            user.save()

            messages.add_message(
                request,
                messages.INFO,
                _("You can now log in using your new password."))
            return redirect(request, 'mediagoblin.auth.login')
        else:
            return render_to_response(
                request,
                'mediagoblin/plugins/basic_auth/change_fp.html',
                {'cp_form': cp_form})

    # in case there is a valid id but no user with that id in the db
    # or the token expired
    else:
        return render_404(request)


def _process_for_token(request):
    """
    Checks for tokens in formdata without prior knowledge of request method

    For now, returns whether the userid and token formdata variables exist, and
    the formdata variables in a hash. Perhaps an object is warranted?
    """
    # retrieve the formdata variables
    if request.method == 'GET':
        formdata_vars = request.GET
    else:
        formdata_vars = request.form

    formdata = {
        'vars': formdata_vars,
        'has_userid_and_token':
            'userid' in formdata_vars and 'token' in formdata_vars}

    return formdata
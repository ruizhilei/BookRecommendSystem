# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length

class RegisterForm(FlaskForm):
    username = StringField("用户名", validators=[DataRequired(), Length(3, 64)])
    email = StringField("邮箱", validators=[DataRequired(), Email()])
    password = PasswordField(
        "密码", validators=[DataRequired(), Length(6, 128)]
    )
    password2 = PasswordField(
        "重复密码",
        validators=[DataRequired(), EqualTo("password", message="两次输入密码不一致")],
    )
    submit = SubmitField("注册")

class LoginForm(FlaskForm):
    email = StringField("邮箱", validators=[DataRequired(), Email()])
    password = PasswordField("密码", validators=[DataRequired()])
    submit = SubmitField("登录")


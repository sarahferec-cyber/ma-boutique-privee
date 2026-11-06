
import streamlit as st

 

import pandas as pd

 

import requests

 

import re

 

import unicodedata

 

import json

 

import base64

import sqlite3

import hashlib

import hmac

import secrets

from datetime import datetime, date, timedelta

from io import BytesIO

from xml.sax.saxutils import escape

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether

from reportlab.lib import colors

from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from reportlab.lib.enums import TA_CENTER

from reportlab.lib.pagesizes import A4

 

 

 

# ============================================================

 

# CONFIGURATION ET CONSTANTES

 

# ============================================================

 

NOM_BOUTIQUE = "Les Bons Plans de Sarah 🌸"

 

 

 

GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1ZtcJ0Wz9mZcqbyd_jnT33_Q7ebfRhgPLddRUWi7NjYA/edit"

 

 

 

STOCK_API_URL = st.secrets.get("STOCK_API_URL", "").strip()
STOCK_API_KEY = st.secrets.get("STOCK_API_KEY", "").strip()

 

 # DISCORD_WEBHOOK : configurer uniquement dans les Secrets Streamlit (valeur masquée)

 

 

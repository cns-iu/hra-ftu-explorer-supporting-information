# commonly used packages in this workflow
from pprint import pprint
import requests
import pandas as pd

a = "This is shared variable"

def print_shared():
  print("This is a shared function.")
  
  
def foo_bar():
  print("AND I AM ALSO SHARED!")
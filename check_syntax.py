import ast
for f in ["app.py", "ai_service.py"]:
    try:
        ast.parse(open(f).read())
        print(f + ": OK")
    except SyntaxError as e:
        print(f + ": ERROR - " + str(e))

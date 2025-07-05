import os, sys, yaml

REQUIRED_TOP_LEVEL = ['version', 'meta', 'source', 'extract', 'alert']

def validate_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            print(f"❌ YAML syntax error in {path}:\n{e}")
            return False

    if not isinstance(data, dict):
        print(f"❌ {path} does not contain a top-level dictionary")
        return False

    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            print(f"❌ Missing required section `{key}` in {path}")
            return False

    print(f"✅ {path} is valid")
    return True

def walk_templates(root_dir):
    all_ok = True
    for dirpath, _, filenames in os.walk(root_dir):
        for file in filenames:
            if file.endswith('.yaml'):
                full_path = os.path.join(dirpath, file)
                ok = validate_file(full_path)
                if not ok:
                    all_ok = False
    return all_ok

if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "templates"
    success = walk_templates(root)
    sys.exit(0 if success else 1)

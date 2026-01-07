# Installation Guide

There are three ways to install AfterThought for global terminal access:

## Option 1: pipx (Recommended) ⭐

pipx installs CLI tools in isolated environments but makes them globally available.

### Install pipx (if not already installed)
```bash
brew install pipx
pipx ensurepath
```

### Install AfterThought
```bash
cd /path/to/AfterThought
pipx install .
```

### Usage
Now you can run `afterthought` from anywhere:
```bash
afterthought
afterthought -c "Lex Fridman" --fetch-missing
afterthought --stats
```

### Update AfterThought
```bash
cd /path/to/AfterThought
git pull
pipx reinstall afterthought
```

### Uninstall
```bash
pipx uninstall afterthought
```

---

## Option 2: Regular pip install with entry point

Install AfterThought into your global Python environment (or a dedicated venv).

```bash
cd /path/to/AfterThought
pip install -e .
```

The `-e` flag installs in "editable" mode, so changes to the code take effect immediately.

### Usage
```bash
afterthought
afterthought -c "History of Rome"
```

### Uninstall
```bash
pip uninstall afterthought
```

---

## Option 3: Shell script wrapper

Create a shell script that activates your venv and runs the command.

### Create the wrapper script
```bash
# Copy the provided afterthought.sh to a directory in your PATH
cp afterthought.sh /usr/local/bin/afterthought
chmod +x /usr/local/bin/afterthought
```

### Edit the script
Update the paths in the script:
- `VENV_PATH`: Path to your virtual environment
- `PROJECT_PATH`: Path to AfterThought directory

### Usage
```bash
afterthought
afterthought -c "All-In"
```

---

## Verify Installation

After installation with any method, verify it works:

```bash
afterthought --help
```

You should see the help text with all available options.

---

## Configuration

Regardless of installation method, you need to configure your `.env` file:

```bash
cd /path/to/AfterThought
cp .env.example .env
# Edit .env with your settings
```

**Important:** The `.env` file must be in the AfterThought directory. The tool will look for it there.

---

## Recommendation

**Use pipx** if you want:
- ✅ Clean installation
- ✅ Isolated dependencies
- ✅ Easy updates
- ✅ No venv activation needed

**Use pip install -e** if you want:
- ✅ To modify the code frequently
- ✅ Immediate reflection of changes
- ✅ Simpler setup

**Use shell wrapper** if you:
- ✅ Want to keep everything in a venv
- ✅ Prefer full control over the environment
- ✅ Don't want to install anything globally

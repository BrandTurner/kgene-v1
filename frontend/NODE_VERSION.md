# Node.js Version Management

## Current Version: 24.11.1

This project uses **Node.js v24.11.1** (LTS) for development and deployment.

---

## How .nvmrc Works

The `.nvmrc` file specifies the Node version, but behavior varies by environment:

### Local Development (Manual)

**By default, .nvmrc is NOT automatic.** You must manually run:

```bash
# When you open a new terminal in the frontend/ directory
nvm use

# Output: Found '/path/to/frontend/.nvmrc' with version <24.11.1>
# Now using node v24.11.1 (npm v10.9.0)
```

**You need to do this:**
- Every time you open a new terminal session
- After switching to this project from another
- When you `cd` into the frontend directory

---

### Make it Automatic (Optional Setup)

You can configure your shell to auto-switch Node versions when entering directories with `.nvmrc`.

#### For Zsh (macOS default):

Add to `~/.zshrc`:

```bash
# Automatically switch Node version based on .nvmrc
autoload -U add-zsh-hook
load-nvmrc() {
  local nvmrc_path="$(nvm_find_nvmrc)"

  if [ -n "$nvmrc_path" ]; then
    local nvmrc_node_version=$(nvm version "$(cat "${nvmrc_path}")")

    if [ "$nvmrc_node_version" = "N/A" ]; then
      nvm install
    elif [ "$nvmrc_node_version" != "$(nvm version)" ]; then
      nvm use
    fi
  elif [ -n "$(PWD=$OLDPWD nvm_find_nvmrc)" ] && [ "$(nvm version)" != "$(nvm version default)" ]; then
    echo "Reverting to nvm default version"
    nvm use default
  fi
}
add-zsh-hook chpwd load-nvmrc
load-nvmrc
```

Then restart your terminal or run: `source ~/.zshrc`

#### For Bash:

Add to `~/.bashrc` or `~/.bash_profile`:

```bash
# Automatically switch Node version based on .nvmrc
cdnvm() {
    command cd "$@" || return $?
    nvm_path=$(nvm_find_nvmrc)

    if [[ -n $nvm_path ]]; then
        nvm use
    fi
}
alias cd='cdnvm'
```

Then: `source ~/.bashrc`

---

### CI/CD & Deployment (Usually Automatic)

Most deployment platforms **automatically detect** `.nvmrc`:

#### ✅ Automatic Detection

- **GitHub Actions**: Use `setup-node` action with `node-version-file: '.nvmrc'`
  ```yaml
  - uses: actions/setup-node@v4
    with:
      node-version-file: '.nvmrc'
  ```

- **Heroku**: Automatically reads `.nvmrc` during build
  ```
  # No configuration needed!
  ```

- **Netlify**: Detects `.nvmrc` automatically
  ```
  # No configuration needed!
  ```

- **Vercel**: Reads `.nvmrc` by default
  ```
  # No configuration needed!
  ```

- **Render**: Detects `.nvmrc` automatically
  ```
  # No configuration needed!
  ```

#### ⚠️ Docker (Does NOT use .nvmrc)

Docker uses the `FROM` directive in `Dockerfile`:

```dockerfile
# Dockerfile specifies Node version directly
FROM node:24.11.1-alpine

# .nvmrc is ignored in Docker builds
```

**Why?** Docker containers don't use nvm - they bake the Node version into the image.

---

## Verification

Check which Node version you're using:

```bash
node --version
# Should output: v24.11.1
```

Check if you're in the right directory with nvm:

```bash
nvm current
# Should output: v24.11.1
```

---

## Troubleshooting

### "nvm: command not found"

nvm is not installed or not loaded in your shell.

**Solution:**
1. Check if nvm is installed: `ls ~/.nvm`
2. Add to `~/.zshrc` or `~/.bashrc`:
   ```bash
   export NVM_DIR="$HOME/.nvm"
   [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
   ```
3. Restart terminal or `source ~/.zshrc`

### "Version '24.11.1' not found"

You don't have Node 24.11.1 installed via nvm.

**Solution:**
```bash
nvm install 24.11.1
nvm use 24.11.1
```

### Wrong Node version after `cd frontend/`

You haven't run `nvm use` yet (unless you set up auto-switching above).

**Solution:**
```bash
nvm use
```

---

## Summary

| Environment | Automatic? | How It Works |
|-------------|-----------|--------------|
| **Local Dev** | ❌ No (by default) | Run `nvm use` manually each time |
| **Local Dev** | ✅ Yes (if configured) | Shell hook auto-switches on `cd` |
| **GitHub Actions** | ✅ Yes | Use `node-version-file: '.nvmrc'` |
| **Heroku/Netlify/Vercel** | ✅ Yes | Platform detects `.nvmrc` automatically |
| **Docker** | ❌ No | Use `FROM node:24.11.1` in Dockerfile |

---

## Recommendation

**For daily development:**
- Set up auto-switching (zsh/bash hook above) - saves time!
- OR remember to run `nvm use` when entering the frontend directory

**For deployment:**
- `.nvmrc` works automatically on most platforms
- For Docker, we'll set `FROM node:24.11.1-alpine` in Dockerfile

---

**Current Status:**
- ✅ `.nvmrc` created with `24.11.1`
- ✅ Matches your global nvm version
- ✅ `@types/node@24.10.1` installed and compatible
- ✅ Ready for development and deployment

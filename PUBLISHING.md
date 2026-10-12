# Putting the site online

Nothing goes online without you approving it. Two gates:

1. **Every publish waits for you.** Each time the site is rebuilt (after any change to
   `main`), GitHub stops before going live and shows a **Review deployments** button.
   Nothing changes on the public site until you click **Approve and deploy**.
2. **New publications arrive as a pull request.** The Monday sync never edits `main`. It opens
   a pull request listing the new papers; you merge it or close it. Merging then still hits gate 1.

The plan below first puts the site at a **test address** next to your current al-folio site,
so the live lab site is untouched until you decide to switch (Part C).

---

## Part A: one-time setup (about 20 minutes)

### 1. Install git (skip if `git --version` works in a terminal)
- Mac: run `xcode-select --install`, or install from https://git-scm.com
- Windows: https://git-scm.com/download/win (accept the defaults)

### 2. Create an empty repository on GitHub
1. Log in to GitHub as the account that owns `swaminathanlab`
   (or the organisation, if `swaminathanlab` is one).
2. Top right **+** → **New repository**.
3. Owner: `swaminathanlab`. Name: `lcmm-website`.
4. **Public** (needed for the approval gate on a free GitHub plan).
5. Leave "Add a README", ".gitignore" and "license" **unticked**. → **Create repository**.

### 3. Check the address in the site
Unzip `lcmm-website.zip`. `mkdocs.yml` is already set to the test address:
```yaml
site_url: https://swaminathanlab.github.io/lcmm-website/
repo_url: https://github.com/swaminathanlab/lcmm-website
```
Change both only if you used a different account or repository name.

### 4. Push the files
In a terminal:
```bash
cd path/to/lcmm-website          # the unzipped folder
git remote add origin https://github.com/swaminathanlab/lcmm-website.git
git push -u origin main
```
If git asks for a password, use a GitHub **personal access token**, not your password
(GitHub → your avatar → Settings → Developer settings → Personal access tokens →
Fine-grained → Generate; give it access to this repository with "Contents: Read and write").
Or use GitHub Desktop (https://desktop.github.com): *File → Add local repository*, pick the
folder, then *Publish*.

The push starts a build that fails or stalls at "deploy". That is expected until steps 5–7 are done.

### 5. Turn on GitHub Pages
Repository → **Settings** → **Pages** → *Build and deployment* → Source: **GitHub Actions**.

### 6. Turn on the approval gate (gate 1)
Repository → **Settings** → **Environments** → **github-pages**
(if it is not listed: **New environment**, name it exactly `github-pages`).
- Tick **Required reviewers** → add yourself → **Save protection rules**.
- *Deployment branches and tags*: **Selected branches** → add `main`.

### 7. Let the publication sync open pull requests (gate 2)
Repository → **Settings** → **Actions** → **General** → *Workflow permissions*:
- **Read and write permissions**
- Tick **Allow GitHub Actions to create and approve pull requests** → **Save**.

### 8. First publish
1. Repository → **Actions** tab → **Build and publish site** → **Run workflow** → Run.
2. When the run shows *Waiting*, click it → **Review deployments** → tick `github-pages` →
   **Approve and deploy**.
3. After about a minute the site is at **https://swaminathanlab.github.io/lcmm-website/**.
   GitHub also emails you whenever a deploy is waiting for approval.

---

## Part B: everyday updates

**Small edits in the browser** (text, people, news):
1. Open the file on GitHub (e.g. `data/people.yaml`) → pencil icon → edit.
2. **Commit changes**. Choose *Create a new branch and start a pull request* if you want to
   look at it before it is merged, or commit directly to `main`.
3. Actions → the run waits → **Review deployments** → **Approve and deploy**.

**Adding images to the home page gallery:**
1. Repository → `data/gallery/` → **Add file** → **Upload files** → drag in images (JPG, PNG,
   TIFF, WebP) or short looping videos (MP4, WebM). Full-resolution files are fine; the build
   makes web-sized copies.
2. Optional: captions, credits and order in `data/gallery.yaml`.
3. Commit, then approve the deploy.
GitHub refuses single files over 100 MB, and a repository should stay under about 1 GB in total,
so export very large TIFF stacks as a single JPEG/PNG frame or a short MP4 first.

**Photos of people:** upload to `data/photos/` named after the person's `id` in
`data/people.yaml` (e.g. `linn-engstrom.jpg`).

**New publications:** on Mondays you may get a pull request "New publications (date)".
Open it → *Files changed* → check → **Merge pull request** (or close it), then approve the deploy.

**Preview before approving:** every pull request build has a downloadable preview
(the run's page → *Artifacts* → `site-preview`; unzip, open `index.html`).

**Undo a bad publish:** Actions → an earlier successful *Build and publish site* run →
**Re-run all jobs** → approve. That puts the older version back online.

---

## Part C: replacing the current al-folio site (when you are happy with the test site)

Your current site is served from the repository `swaminathanlab.github.io`. To switch:

Between steps 1 and 4 the lab address shows nothing for a few minutes, so do it in one go.

1. **Keep the old site recoverable:** that repository → Settings → rename it to
   `old-website-alfolio`, then *Archive this repository* (Settings, bottom). Nothing is deleted.
2. **Rename the new one:** `lcmm-website` → Settings → rename to `swaminathanlab.github.io`.
3. In `mkdocs.yml`, set
   `site_url: https://swaminathanlab.github.io/` and
   `repo_url: https://github.com/swaminathanlab/swaminathanlab.github.io`, commit.
4. Repeat Part A steps 5–6 on the renamed repository if they are not carried over, then
   approve the deploy. The site is now at **https://swaminathanlab.github.io/**.

Custom domain later (e.g. `lcmm.lu.se` or similar): Settings → Pages → Custom domain, a DNS
record from whoever runs the domain (for lu.se, Lund University IT), and update `site_url`.

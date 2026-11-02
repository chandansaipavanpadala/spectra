# 🎓 Amrita Vishwa Vidyapeetham — Reusable Beamer Presentation Template

A modular, pixel-perfect, academic presentation system designed for B.Tech / M.Tech / Ph.D. project defenses, milestones, and technical seminars at Amrita Vishwa Vidyapeetham.

Built strictly in accordance with institutional formatting rules:
- **Geometry**: 16:9 widescreen format (`aspectratio=169`, 11pt)
- **Typography**: Strict Times New Roman across all body text, headings, and math (`\usefonttheme{serif}`, `mathptmx`)
- **Visual Design**: High-contrast, publication-grade frosted glassmorphism (`tcolorbox`), crisp pure black typography (`#000000`), subtle glazed card rims, and dynamic slide numbering
- **Self-Contained**: Portable modular package (`beamer_amrita_theme.sty`) and pre-bundled institutional logo assets

---

## 📂 Directory Layout

```text
Presentations/Template/
├── README.md                               # This documentation & macro manual
├── beamer_amrita_theme.sty                 # Core modular presentation style package
├── template.tex                            # Starter presentation boilerplate (10 core slide archetypes)
├── template_preview.pdf                    # Compiled reference PDF preview
├── Amrita-vishwa-vidyapeetham-dark-logo.png  # High-contrast charcoal/black institutional logo
├── Amrita-vishwa-vidyapeetham-color-logo.png # Official Amrita maroon/gold institutional logo
├── Amrita-vishwa-vidyapeetham-white-logo.png # High-contrast white logo (for dark theme)
├── background-gradient.png                 # Subtle warm peach gradient canvas asset
├── build/                                  # Compilation intermediate files (.aux, .log, .nav, .snm, .toc)
└── rendered_slides/                        # High-resolution PNG preview renders of each slide archetype
```

---

## 🚀 Quick-Start Guide: Creating a New Presentation

To start a new evaluation deck (e.g., `Presentations/Evaluation III`):

1. **Copy the Template Folder:**
   ```powershell
   Copy-Item -Recurse "Presentations/Template" "Presentations/Evaluation III"
   ```

2. **Configure Preamble Variables in `template.tex` (or rename to `main.tex`):**
   Open the file and update the configuration block at lines 6–34:

   ```latex
   % =============================================================================
   % 1. PRESENTATION METADATA CONFIGURATION (EDIT FOR EACH REVIEW)
   % =============================================================================
   \newcommand{\reviewBanner}{EVALUATION III}                           % Review badge
   \newcommand{\presentationTitle}{YOUR PROJECT TITLE IN UPPERCASE}    % Project title
   \newcommand{\presentationSubtitle}{23ECE498 --- PROJECT PHASE II}   % Course code
   \newcommand{\academicYear}{AY 2026--2027}

   % Team Member Credentials
   \newcommand{\memberOneRoll}{BL.EN.U4ECE23XXX}
   \newcommand{\memberOneName}{First Student Name}
   \newcommand{\memberTwoRoll}{BL.EN.U4ECE23XXX}
   \newcommand{\memberTwoName}{Second Student Name}
   \newcommand{\memberThreeRoll}{BL.EN.U4ECE23XXX}
   \newcommand{\memberThreeName}{Third Student Name}

   % Faculty & Evaluation Panel
   \newcommand{\guideName}{Dr. S. Lalitha}
   \newcommand{\evaluatorOne}{Dr. Susmitha Vekkot}
   \newcommand{\evaluatorTwo}{Dr. Vivek Venugopal}

   % Footer Branding
   \newcommand{\footerTeamName}{Team DHV\={A}N\={I}}                   % Displayed bottom-left
   \newcommand{\totalSlideCount}{10}                                  % Optional fixed slide count

   % Logo Variant (dark-logo, color-logo, or white-logo)
   \newcommand{\logoAsset}{Amrita-vishwa-vidyapeetham-dark-logo.png}

   % Toggle Background (uncomment for peach gradient; comment out for clean white)
   \def\useGradientBackground{1}
   ```

3. **Edit Your Slides & Compile!**

---

## 🛠 Compilation Workflow

Compile using standard `pdflatex` (two passes recommended for dynamic page numbering and cross-references):

### PowerShell (Windows)
```powershell
cd "Presentations/Template"
if (!(Test-Path "build")) { New-Item -ItemType Directory -Path "build" }
pdflatex -interaction=nonstopmode -output-directory=build template.tex
pdflatex -interaction=nonstopmode -output-directory=build template.tex
Copy-Item "build/template.pdf" "template_preview.pdf" -Force
```

### Bash (Linux / macOS)
```bash
cd Presentations/Template
mkdir -p build
pdflatex -interaction=nonstopmode -output-directory=build template.tex
pdflatex -interaction=nonstopmode -output-directory=build template.tex
cp build/template.pdf template_preview.pdf
```

---

## 🧩 Visual Macro & Environment Reference

The modular package `beamer_amrita_theme.sty` provides pre-tuned environments designed to prevent vertical overflows:

### 1. Slide Header (`\slideheader{TITLE}`)
Automatically places the institutional logo on the top-right corner with margin adjustment, aligns the bold title, and renders an elegant trailing horizontal rule:
```latex
\begin{frame}[t]
  \slideheader{SYSTEM ARCHITECTURE}
  % Slide content here
\end{frame}
```

### 2. Frosted Glass Box (`\begin{glassbox}[options]{Title}`)
Outlined translucent container with header banner for text, equations, or lists. Also aliased as `\begin{cardbox}[options]{Title}`:
```latex
\begin{glassbox}[top=4pt, bottom=4pt, left=6pt, right=6pt, title=\textbf{Key Takeaways}]{}
  \begin{itemize}
    \item High-speed folding ADC front-end.
    \item Multi-tone spectral reconstruction.
  \end{itemize}
\end{glassbox}
```

### 3. Glass Card Container (`\begin{glasscard}[options]`)
Headerless translucent frosted glass card for arbitrary layouts:
```latex
\begin{glasscard}[top=4pt, bottom=4pt, left=6pt, right=6pt]
  Content inside card...
\end{glasscard}
```

### 4. Graphic Placeholder Container (`\begin{imagebox}{height}`)
Pre-styled container with centered vertical/horizontal alignment and subtle border:
```latex
\begin{imagebox}{4.65cm}
  \includegraphics[width=\linewidth, height=4.5cm, keepaspectratio]{figure.png}
\end{imagebox}
```

### 5. Numbered Process Badges & Cards (`\processcard` and `processcardenv`)
Ideal for objectives, phased milestones, and methodological pipelines:
```latex
% Macro form:
\processcard{1}{Mathematical Formulation}{Derive finite-difference convergence bounds.}

% Environment form:
\begin{processcardenv}{2}{Hardware Design}
  Fabricate 4-layer low-noise IBMADC PCB front-end with ESP32 streaming.
\end{processcardenv}
```

### 6. Progress Dots (`\decorativedots`)
Renders four clean accent dots (`● ● ● ●`) for section transitions or visual dividers:
```latex
\decorativedots
```

---

## 📋 Boilerplate Slide Catalog

`template.tex` includes 10 production-tested slide layouts:

| # | Slide Archetype | Layout Structure | Best Used For |
|---|---|---|---|
| **1** | **Master Title Frame** | Institutional header, review badge, title, 2-column team & faculty credentials | Opening title slide |
| **2** | **Agenda / Table of Contents** | 2-column bento grid with numbered index pills (10 sections) | Presentation overview |
| **3** | **Standard 2-Column Concept** | Left: structured bulleted glass box; Right: visual container + caption | Problem definition, motivation |
| **4** | **Process / Objectives** | 3 stacked horizontal process cards with numeric circular badges | Research objectives, methodology |
| **5** | **Mathematical Derivation** | Left: equation box; Right: parameter notation table (`tabularx`) | Analytical formulations, theorems |
| **6** | **Full-Width Graphic Container** | Centered high-resolution image container (`0.92\textwidth`, 4.8cm height) | Architecture diagrams, signal plots |
| **7** | **Comparative Benchmark Table** | Clean academic `booktabs` table with aligned headers and bold winners | State-of-the-art comparison |
| **8** | **Roadmap & Milestones** | Side-by-side milestone cards (Phase 1 Completed vs. Phase 2 Targets) | Project timeline, future scope |
| **9** | **Formal References** | Standard IEEE numbered bibliography card | Literature citations |
| **10** | **Closing / Q&A Frame** | Centered bold `THANK YOU`, discussion prompt, team & department branding | Conclusion, defense questions |

---

## 🎨 Design Rules & Best Practices

1. **Avoid Text Overflows:**
   - Keep column widths to `0.485\textwidth` when using two columns inside a frame.
   - Use `\begin{frame}[t]` (top-aligned) to maintain consistent baseline alignment across slides.
   - For bullet points, set `\fontsize{8.2pt}{10.5pt}\selectfont` to achieve crisp, legible, and balanced layouts without crowding.

2. **Logo Positioning:**
   - The top banner logo is offset by `\hspace*{-0.80cm}` to cleanly align with the outer margin of the slide.

3. **Color Contrast:**
   - Pure black (`#000000`) is used for all text, headings, formulas, and borders to ensure maximum legibility when projected in lecture halls and evaluation rooms.

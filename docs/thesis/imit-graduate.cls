\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{imit-graduate}[2026/10/27 LaTeX class for student papers]

\newif\ifpapertypedefined
\newif\ifbachelor
\newif\ifmaster
\newif\iftermpaper
\newif\ifessay

\newif\ifdocumenttypedefined
\newif\ifnotassign
\newif\ifassign
\newif\ifpaper
\newif\ifsummary

\newif\ifwindows

\newif\ifappendix

\DeclareOption{bachelor}{\bachelortrue}
\DeclareOption{master}{\mastertrue}
\DeclareOption{termpaper}{\termpapertrue}
\DeclareOption{essay}{\essaytrue}

\DeclareOption{assignment}{\assigntrue}
\DeclareOption{paper}{\papertrue}
\DeclareOption{summary}{\summarytrue}

\DeclareOption{cp1251}{\windowstrue}
\ProcessOptions\relax

\ifbachelor
    \papertypedefinedtrue
    \ifmaster
        \error{Incompatible options: 'bachelor' and 'master'}
    \fi
    \iftermpaper
        \error{Incompatible options: 'bachelor' and 'termpaper'}
    \fi
    \ifessay
        \error{Incompatible options: 'bachelor' and 'essay'}
    \fi
\fi
\ifmaster
    \papertypedefinedtrue
    \iftermpaper
        \error{Incompatible options: 'master' and 'termpaper'}
    \fi
    \ifessay
        \error{Incompatible options: 'master' and 'essay'}
    \fi
\fi
\iftermpaper
    \papertypedefinedtrue
    \ifessay
        \error{Incompatible options: 'termpaper' and 'essay'}
    \fi
\fi
\ifessay
    \papertypedefinedtrue
\fi
\ifpapertypedefined\else
    \error{Paper type is not defined: 'bachelor', 'master', 'termpaper', or 'essay'}
\fi

\ifassign
    \documenttypedefinedtrue
    \ifpaper
        \error{Incompatible options: 'assignment' and 'paper'}
    \fi
    \ifsummary
        \error{Incompatible options: 'assignment' and 'summary'
    \fi
    \ifessay
        \error{Incompatible options: 'assignment' and 'essay'}
    \fi
\fi
\ifpaper
    \documenttypedefinedtrue
    \notassigntrue
    \ifsummary
        \error{Incompatible options: 'summary' and 'paper'}
    \fi
\fi
\ifsummary
    \documenttypedefinedtrue
    \notassigntrue
    \ifbachelor
        \error{Incompatible options: 'summary' and 'bachelor'}
    \fi
    \iftermpaper
        \error{Incompatible options: 'summary' and 'termpaper'}
    \fi
    \ifessay
        \error{Incompatible options: 'summary' and 'essay'}
    \fi
\fi
\ifdocumenttypedefined\else
    \error{Document type is not defined: 'paper', 'assignment', or 'summary'}
\fi


\ifassign
    \ifbachelor
        \LoadClass[14pt,a4paper,landscape]{extarticle}
    \fi %\ifbachelor
    \ifmaster
        \LoadClass[12pt,a4paper]{extarticle}
    \fi %\ifmaster
    \iftermpaper
        \LoadClass[14pt,a4paper,landscape]{extarticle}
    \fi %\iftermpaper
\fi %\ifassign
\ifpaper
    \ifessay
        \LoadClass[14pt,a4paper]{extarticle}
    \else
        \LoadClass[14pt,a4paper]{extreport}
    \fi %\ifessay
\fi %\ifpaper
\ifsummary
    \LoadClass[10pt,a5paper,twoside]{extarticle}
\fi %\ifsummary

\ifwindows
    \RequirePackage[cp1251]{inputenc}
\else  %\ifwindows
    \RequirePackage[utf8]{inputenc}
\fi %\ifwindows
\RequirePackage[T2A]{fontenc}
\RequirePackage[english,russian]{babel}
\RequirePackage{tocloft}
\RequirePackage{indentfirst}
\RequirePackage{graphicx}
\RequirePackage{longtable}
\RequirePackage{ragged2e}
\RequirePackage{tabu}
\RequirePackage{enumitem}
\RequirePackage{xcolor}
\RequirePackage{environ}
\RequirePackage{trimspaces}
\usepackage[activate={true,nocompatibility},final=true]{microtype}
\usepackage[svgnames]{xcolor}
\usepackage{caption}
\usepackage{fancyhdr}
\usepackage{titlesec}
\usepackage{csquotes}

\ifsummary
    \def\defernumbersoption{defernumbers=true,}
\else
    \def\defernumbersoption{}
\fi %\ifsummary

\usepackage[backend=biber,%
        maxnames=3,minnames=3,%
        style=gost-numeric,%
%        useauthor=false,%
        language=auto, % \IeC {\cyrp }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \IeC {\cyrya }\IeC {\cyrz }\IeC {\cyrery }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyri }\IeC {\cyrz } babel
        autolang=other,%
        otherlangs=true,%
        \defernumbersoption
        sorting=nty]{biblatex}
        
\usepackage[unicode,colorlinks,linkcolor=blue,draft=false,breaklinks,bookmarksopen,pdflang=ru-RU]{hyperref}
\usepackage[russian]{varioref}

\def\assignfont{\upshape}

\addto\extrasrussian{%
	\def\reftextfaraway#1{\IeC {\cyrn }\IeC {\cyra }~\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrr }.\,\pageref{#1}}%
	\def\reftextpagerange#1#2{\IeC {\cyrn }\IeC {\cyra }~\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrr }.\,\pageref{#1}--\pageref{#2}}%
}

\def\bibname{\IeC {\CYRS }\IeC {\cyrp }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyro }\IeC {\cyrk } \IeC {\cyrl }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyru }\IeC {\cyrr }\IeC {\cyrery }}
\def\selfbibname{\IeC {\CYRP }\IeC {\cyru }\IeC {\cyrb }\IeC {\cyrl }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyri }}

\ifnotassign
    \linespread{1.15}
    
    \renewcommand*{\mkgostheading}[1]{{\slshape #1}}
    \renewcommand*{\revsdnamepunct}{,\addspace}
    \DeclareFieldFormat{labelnumberwidth}{[#1]}
    \def\printthebibliography{%
        \clearpage
        \phantomsection
        \ifessay
	        \addcontentsline{toc}{section}{\bibname}%
        \else
	        \addcontentsline{toc}{chapter}{\bibname}%
        \fi
        \toggletrue{bbx:gostbibliography}%
        \printbibliography[title={\bibname}]}
    \def\printfullbibliography{%
        \nocite{*}
        \phantomsection
        \ifessay
	        \addcontentsline{toc}{section}{\bibname}%
        \else
	        \addcontentsline{toc}{chapter}{\bibname}%
        \fi
        \toggletrue{bbx:gostbibliography}%
        \printbibliography[title={\bibname}]}
    \def\printselfbibliography{%
        \nocite{*}
        \toggletrue{bbx:gostbibliography}%
        \oldsection*{\selfbibname}%
        \printbibliography[%
            resetnumbers=1,%
            heading=none,%
            keyword=self%
            ]}
    
    \let\oldappendix\appendix
    \let\oldchapter\chapter
    \let\oldsection\section
    \let\oldsubsection\subsection
    \let\oldsubsubsection\subsubsection

    \ifpaper
        \makeatletter
        \def\sectionsign{\S\,}
        \def\appendix@chapter#1{%
            \refstepcounter{chapter}%
            \oldchapter*{\IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrl }\IeC {\cyro }\IeC {\cyrzh }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \Asbuk{chapter}\\{}#1}%
            \addcontentsline{toc}{chapter}{\IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrl }\IeC {\cyro }\IeC {\cyrzh }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \Asbuk{chapter}. {}#1}%
            }
        \def\appendix{%
            \oldappendix
            \appendixtrue
            \def\sectionsign{}
            \let\chapter\appendix@chapter
            \def\section{\oldsection*}%
            \def\subsection{\oldsubsection*}%
            \def\subsubsection{\oldsubsubsection*}%
            }
            
        \def\cftchapleader{\cftdotfill{\cftdotsep}}
%        \def\l@chapter#1#2{{\vbox{\linespread{1}\bfseries\def\numberline##1{\IeC {\CYRG }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrv }\IeC {\cyra } ##1. }%
%            \strut#1\cftdotfill{\cftdotsep}#2}}}
        \ifessay
            \def\l@section#1#2{{\vbox{\linespread{1}\bfseries\def\numberline##1{##1.\,}%
            \strut#1\cftdotfill{\cftdotsep}#2}}}
            \renewcommand{\thesection}{\sectionsign\arabic{section}}
            \renewcommand{\thesubsection}{\thesection.\arabic{subsection}}
            \renewcommand{\thesubsubsection}{\thesubsection.\arabic{subsubsection}}
%            \titleformat*{\section}{\raggedright\bfseries\LARGE}
%            \titleformat*{\subsection}{\raggedright\slshape\bfseries\Large}
%            \titleformat*{\subsubsection}{\raggedright\slshape\bfseries\large}
        \else
%            \def\l@chapter#1#2{{\vbox{\linespread{1}\bfseries\def\numberline##1{Глава ##1.\kern0.3em}%
%            \strut#1\cftdotfill{\cftdotsep}#2}}}
            \renewcommand{\thesection}{\sectionsign\thechapter.\arabic{section}}
            \renewcommand{\thesubsection}{\thesection.\arabic{subsection}}
            \renewcommand{\thesubsubsection}{\thesubsection.\arabic{subsubsection}}
%            \titleformat*{\section}{\raggedright\bfseries\LARGE}
%            \titleformat*{\subsection}{\raggedright\slshape\bfseries\Large}
%            \titleformat*{\subsubsection}{\raggedright\slshape\bfseries\large}
	        \setlength\cftchapnumwidth{4.8em}
	        \def\cftchappresnum{{\IeC {\CYRG }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrv }\IeC {\cyra }\space}}
	        \def\cftchapaftersnum{.}
	        \def\cftchapaftersnumb{}
        \fi %\ifessay
        \titleformat{\section}{\raggedright\bfseries\LARGE}{\thesection.}{0.5em}{}
        \def\cftsecaftersnum{.}
        \def\cftsecaftersnumb{\kern0.2em}
        \titleformat{\subsection}{\raggedright\slshape\bfseries\Large}{\thesubsection.}{0.5em}{}
        \def\cftsubsecaftersnum{.}
        \def\cftsubsecaftersnumb{\kern0.2em}
        \titleformat{\subsubsection}{\raggedright\slshape\bfseries\large}{\thesubsubsection.}{0.5em}{}
        \def\cftsubsubsecaftersnum{.}
        \def\cftsubsubsecaftersnumb{\kern0.2em}
    
        \makeatother
        
        \fancyhead[L]{}
        \fancyhead[R]{\thepage}
        \fancyfoot[L,C,R]{}
    \fi %\ifpaper
    \ifsummary
        \def\section{\oldsection*}%
        \def\subsection{\oldsubsection*}%
        \def\subsubsection{\oldsubsubsection*}%
        
        \fancyfoot[C]{\thepage}
        \renewcommand{\headrulewidth}{0pt}
    \fi %\ifsummary
    
    \captionsetup[figure]{name={\IeC {\CYRR }\IeC {\cyri }\IeC {\cyrs }.},labelsep=period}
    \captionsetup[table]{name={\IeC {\CYRT }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyrl }\IeC {\cyri }\IeC {\cyrc }\IeC {\cyra }},labelsep=period}
    \captionsetup[lstlisting]{labelsep=period}
        
    \def\textso#1{\textls[200]{#1}}
    \def\so{\SetTracking{encoding=*}{200}\lsstyle}
    \let\emph\textso
    \let\em\so
       
\fi %\ifnotassign

\ifassign
    \ifbachelor
        \voffset=-1in
        \topmargin=15mm
        \headheight=0mm
        \headsep=0mm
        \textheight=180mm
        
        \hoffset=-1in
        \oddsidemargin=10mm
        \evensidemargin=10mm
        \textwidth=277mm
        \def\pagewidth{128.3mm}
        \def\pagesep{20mm}
    \fi %\ifbachelor
    
    \iftermpaper
        \voffset=-1in
        \topmargin=15mm
        \headheight=0mm
        \headsep=0mm
        \textheight=180mm
        
        \hoffset=-1in
        \oddsidemargin=10mm
        \evensidemargin=10mm
        \textwidth=277mm
        \def\pagewidth{128.3mm}
        \def\pagesep{20mm}
    \fi %\iftermpaper
    
    \ifmaster
        \voffset=-1in
        \topmargin=20mm
        \headheight=0mm
        \headsep=0mm
        \textheight=257mm
        
        \hoffset=-1in
        \oddsidemargin=25mm
        \evensidemargin=15mm
        \textwidth=170mm
    \fi %\ifmaster
\fi %\ifassign

\ifpaper
    \voffset=-1in
    \topmargin=12mm
    \headheight=6.2mm
    \headsep=5mm
    \textheight=255mm
    
    \hoffset=-1in
    \oddsidemargin=25mm
    \evensidemargin=25mm
    \textwidth=170mm
\fi %\ifpaper

\ifsummary
    \voffset=-1in
    \topmargin=15mm
    \headheight=0mm
    \headsep=0mm
    \textheight=175mm
    
    \hoffset=-1in
    \oddsidemargin=20mm
    \evensidemargin=15mm
    \textwidth=113.50mm
\fi %\ifpaper

\ifassign
    \pagestyle{empty}
\fi %\ifassign
\ifsummary
    \pagestyle{plain}
\fi %\ifsummary
\ifpaper
    \pagestyle{fancy}
    \fancypagestyle{plain}[fancy]{}
\fi %\ifpaper

\makeatletter

\let\brief\relax
\let\position\relax
\let\degree\relax
\let\rank\relax
\let\english\relax
\let\result\relax
\def\emptymacro{}

\def\ye@r#1-#2\@nd{%
    \def\yeari{#1}%
    \def\yearii{#2}%
}
\def\year#1{\ye@r#1\@nd}

\def\orderdatename{\underline{\hspace*{25mm}}}
\def\ordernumbername{\underline{\hspace*{18mm}}}
\def\order#1#2{%
    \iftermpaper
        \error{Incompatible command: 'order' is incompatible with 'termpaper'}%
    \fi %\iftermpaper
    \ifessay
        \error{Incompatible command: 'order' is incompatible with 'essay'}%
    \fi %\ifessay
    \def\orderdatename{#1}%
    \def\ordernumbername{#2}%
}

\def\subject#1{%
    \ifbachelor
        \error{Incompatible command: 'subject' is incompatible with 'bachelor'}%
    \fi %\iftermpaper
    \ifmaster
        \error{Incompatible command: 'subject' is incompatible with 'master'}%
    \fi %\ifessay
    \def\subjectname{#1}%
}

\def\stud@nt#1\brief#2\group#3\english#4\@nd{%
    \def\studentname{#1}%
    \def\briefstudentname{#2}%
    \def\groupstudentname{#3}%
    \def\englishstudentname{#4}%
    \trim@spaces@in\studentname
    \trim@spaces@in\briefstudentname
    \trim@spaces@in\groupstudentname
    \trim@spaces@in\englishstudentname
    }
\def\student#1{\stud@nt#1\english\@nd}

\def\supervis@r#1\brief#2\position#3\degree#4\rank#5\@nd{%
    \def\supervisername{#1}%
    \def\briefsupervisername{#2}%
    \def\positionsupervisername{#3}%
    \def\degreesupervisername{#4}%
    \def\ranksupervisername{#5}%
    \trim@spaces@in\supervisername
    \trim@spaces@in\briefsupervisername
    \trim@spaces@in\positionsupervisername
    \trim@spaces@in\degreesupervisername
    \trim@spaces@in\ranksupervisername
}

\def\superviser#1{\supervis@r#1\degree\rank\@nd}

\def\program#1{%
    \def\programname{#1}%
}

\def\titl@#1\english#2\@nd{
    \def\titlename{#1}
    \def\englishtitlename{#2}
    \trim@spaces@in\titlename
    \trim@spaces@in\englishtitlename
    }
\def\title#1{\titl@#1\english\@nd}

\def\goal#1{\def\goalname{#1}}

\def\programnameics{\IeC {\CYRI }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyri } \IeC {\cyrk }\IeC {\cyro }\IeC {\cyrm }\IeC {\cyrp }\IeC {\cyrsftsn }\IeC {\cyryu }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyre } \IeC {\cyrn }\IeC {\cyra }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyri }}
\def\specialitynameics{02.03.02 \IeC {\CYRF }\IeC {\cyru }\IeC {\cyrn }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrm }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrt }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyrsftsn }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyri } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyre } \IeC {\cyrt }\IeC {\cyre }\IeC {\cyrh }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyri }\IeC {\cyri }}
\def\headnameics{\IeC {\CYRS }.\,\IeC {\CYRM }.\,\IeC {\CYRD }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }}
\def\programnameswi{\IeC {\CYRI }\IeC {\cyrn }\IeC {\cyrzh }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrya } \IeC {\cyrp }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrm }\IeC {\cyrm }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyro } \IeC {\cyro }\IeC {\cyrb }\IeC {\cyre }\IeC {\cyrs }\IeC {\cyrp }\IeC {\cyre }\IeC {\cyrch }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrya }}
\def\specialitynameswi{02.03.02 \IeC {\CYRF }\IeC {\cyru }\IeC {\cyrn }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrm }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrt }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyrsftsn }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyri } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyre } \IeC {\cyrt }\IeC {\cyre }\IeC {\cyrh }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyri }\IeC {\cyri }}
\def\headnameswi{\IeC {\CYRS }.\,\IeC {\CYRM }.\,\IeC {\CYRD }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }}
\def\programnameswiai{\IeC {\CYRP }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrm }\IeC {\cyrm }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrzh }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrya } \IeC {\cyrv } \IeC {\cyri }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyru }\IeC {\cyrs }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrm } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrk }\IeC {\cyrt }\IeC {\cyre }}
\def\specialitynameswiai{02.03.02 \IeC {\CYRF }\IeC {\cyru }\IeC {\cyrn }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrm }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrt }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyrsftsn }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyri } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyre } \IeC {\cyrt }\IeC {\cyre }\IeC {\cyrh }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyri }\IeC {\cyri }}
\def\headnameswiai{\IeC {\CYRS }.\,\IeC {\CYRM }.\,\IeC {\CYRD }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }}
\def\programnameaida{\IeC {\CYRI }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyru }\IeC {\cyrs }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrk }\IeC {\cyrt } \IeC {\cyri } \IeC {\cyra }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyri }\IeC {\cyrz } \IeC {\cyrd }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrh }}
\def\specialitynameaida{01.03.02 \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyri } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }}
\def\headnameaida{\IeC {\CYRS }.\,\IeC {\CYRM }.\,\IeC {\CYRD }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }}
\def\programnamemm{\IeC {\CYRM }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrch }\IeC {\cyre }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyre } \IeC {\cyrm }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyri }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre }}
\def\specialitynamemm{01.03.02 \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyri } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }}
\def\headnamemm{\IeC {\CYRS }.\,\IeC {\CYRM }.\,\IeC {\CYRD }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }}
\def\programnamesa{\IeC {\CYRS }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyra }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyri }\IeC {\cyrz }}
\def\specialitynamesa{01.03.02 \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyri } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }}
\def\headnamesa{\IeC {\CYRS }.\,\IeC {\CYRM }.\,\IeC {\CYRD }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }}
\def\programnameicpim{\IeC {\CYRI }\IeC {\cyrn }\IeC {\cyrzh }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyre } \IeC {\cyrk }\IeC {\cyro }\IeC {\cyrm }\IeC {\cyrp }\IeC {\cyrsftsn }\IeC {\cyryu }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyre } \IeC {\cyrp }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyre }\IeC {\cyrk }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \IeC {\cyri } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrd }\IeC {\cyru }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyrsftsn }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }}
\def\specialitynameicpim{01.03.02 \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyri } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }}
\def\headnameicpim{\IeC {\CYRS }.\,\IeC {\CYRM }.\,\IeC {\CYRD }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }}
\def\programnameacse{\IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyrv } \IeC {\cyrerev }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrm }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyre }}
\def\specialitynameacse{09.03.03 \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }}
\def\headnameacse{\IeC {\CYRS }.\,\IeC {\CYRM }.\,\IeC {\CYRD }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }}
\def\programnameacsm{\IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyrv } \IeC {\cyrm }\IeC {\cyre }\IeC {\cyrh }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyre }}
\def\specialitynameacsm{09.03.03 \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }}
\def\headnameacsm{\IeC {\CYRS }.\,\IeC {\CYRM }.\,\IeC {\CYRD }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }}
\def\programnameicmrs{\IeC {\CYRI }\IeC {\cyrn }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrk }\IeC {\cyrt }\IeC {\cyru }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyrsftsn }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyre } \IeC {\cyru }\IeC {\cyrp }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrv }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \IeC {\cyrv } \IeC {\cyrm }\IeC {\cyre }\IeC {\cyrh }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrh } \IeC {\cyri } \IeC {\cyrr }\IeC {\cyro }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrh }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrch }\IeC {\cyre }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyri }\IeC {\cyrh } \IeC {\cyrs }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrh }}
\def\specialitynameicmrs{15.03.06 \IeC {\CYRM }\IeC {\cyre }\IeC {\cyrh }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyri } \IeC {\cyrr }\IeC {\cyro }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrh }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }}
\def\headnameicmrs{\IeC {\CYRS }.\,\IeC {\CYRM }.\,\IeC {\CYRD }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }}
\def\programnamemacsae{\IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyrv } \IeC {\cyra }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrch }\IeC {\cyre }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrerev }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrm }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyre }}
\def\specialitynamemacsae{09.04.03 \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }}
\def\headnamemacsae{\IeC {\CYRG }.\,\IeC {\CYRM }.\,\IeC {\CYRS }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyro }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrh }\IeC {\cyra }}
\def\programnamemista{\IeC {\CYRI }\IeC {\cyrn }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrk }\IeC {\cyrt }\IeC {\cyru }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyrsftsn }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyre } \IeC {\cyrs }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyrery }. \IeC {\CYRT }\IeC {\cyre }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrya } \IeC {\cyri } \IeC {\cyrp }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrl }\IeC {\cyro }\IeC {\cyrzh }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrya }}
\def\specialitynamemista{09.04.03 \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }}
\def\headnamemista{\IeC {\CYRS }.\,\IeC {\CYRM }.\,\IeC {\CYRD }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }}
\def\programnamemsp{\IeC {\CYRS }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyre } \IeC {\cyrp }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrm }\IeC {\cyrm }\IeC {\cyri }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre }}
\def\specialitynamemsp{01.04.02 \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyri } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }}
\def\headnamemsp{\IeC {\CYRS }.\,\IeC {\CYRM }.\,\IeC {\CYRD }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }}
\def\programnamemsa{\IeC {\CYRS }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyra }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyri }\IeC {\cyrz }}
\def\specialitynamemsa{01.04.02 \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyri } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }}
\def\headnamemsa{\IeC {\CYRA }.\,\IeC {\CYRV }.\,\IeC {\CYRYA }\IeC {\cyrz }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrn }}
\def\programnamemitcd{\IeC {\CYRI }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyre } \IeC {\cyrt }\IeC {\cyre }\IeC {\cyrh }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyri }\IeC {\cyri } \IeC {\cyrv } \IeC {\cyru }\IeC {\cyrp }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrv }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyri } \IeC {\cyri } \IeC {\cyrp }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrn }\IeC {\cyrya }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyri } \IeC {\cyrr }\IeC {\cyre }\IeC {\cyrsh }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrishrt }}
\def\specialitynamemitcd{02.04.02 \IeC {\CYRF }\IeC {\cyru }\IeC {\cyrn }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrm }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrt }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyrsftsn }\IeC {\cyrn }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyri } \IeC {\cyri }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyre } \IeC {\cyrt }\IeC {\cyre }\IeC {\cyrh }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyri }\IeC {\cyri }}
\def\headnamemitcd{\IeC {\CYRA }.\,\IeC {\CYRV }.\,\IeC {\CYRYA }\IeC {\cyrz }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrn }}

\def\task#1{\relax}
\def\image{\item}
\def\adviser{\item}

\def\taskt@sk#1\result#2\@nd{\item #1}
\def\tasktask#1{\taskt@sk#1\result\@nd}
\def\taskres@lt#1\result#2\@nd{\item #2}
\def\taskresult#1{\taskres@lt#1\result\@nd}

\let\tasksname\relax
\let\imagesname\relax
\let\advisersname\relax

\NewEnviron{tasks}{\global\let\tasksname\BODY}
\NewEnviron{images}{\global\let\imagesname\BODY}
\NewEnviron{advisers}{\global\let\advisersname\BODY}
\NewEnviron{englishabstract}{\global\let\englishabstractname\BODY}

\def\tablestrut{\vrule width 0mm height 2ex depth 4ex}
\def\itemskip{2mm}
\def\uspace#1{\underline{\hspace*{#1}}}

\AddEnumerateCounter*{\asbuk}{\c@asbuk}{7}
\setlist[enumerate,1]{label={\upshape\mdseries\arabic{*})},itemsep=0mm}
\setlist[enumerate,2]{label={\upshape\asbuk*)},itemsep=0mm}
\setlist[enumerate,3]{label={\upshape\roman*)},itemsep=0mm}

\makeatother

\ifbachelor
    \def\makeassignment{%
    \linespread{1.03}
    \noindent
    \begin{minipage}[t]{\pagewidth}%
    \begin{center}
    {\bfseries \IeC {\CYRK }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrr }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyrg }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrf }\IeC {\cyri }\IeC {\cyrk }}\\
    \IeC {\cyrv }\IeC {\cyrery }\IeC {\cyrp }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyrn }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrya } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR }
    \end{center}
    
    \begin{tabu}{|X[3,L]|X[1,C]|X[1,C]|}
    %\cline{1-3}
    \hline
    \IeC {\CYRV }\IeC {\cyrery }\IeC {\cyrp }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyrn }\IeC {\cyrya }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyra } & \IeC {\CYRS }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrk }\IeC {\cyri } \IeC {\cyrv }\IeC {\cyrery }\IeC {\cyrp }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyrn }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrya } & \IeC {\CYRO }\IeC {\cyrt }\IeC {\cyrm }\IeC {\cyre }\IeC {\cyrt }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyro } \IeC {\cyrv }\IeC {\cyrery }\IeC {\cyrp }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyrn }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyri }\hskip0mm\strut\\
    \hline
    %\cline{1-3}
    \IeC {\CYRV }\IeC {\cyrery }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrr } \IeC {\cyrn }\IeC {\cyra }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyro } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrya }\hskip0mm\strut & 30.09.\yeari\tablestrut& \strut\\
    \cline{1-3}
    \IeC {\CYRV }\IeC {\cyrery }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrr } \IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyrery } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR }\hskip0mm\strut & 30.10.\yeari\tablestrut& \strut\\
    \cline{1-3}
    \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyre }\IeC {\cyrd }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyra }\IeC {\cyrv }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \IeC {\cyrz }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrya } \IeC {\cyrn }\IeC {\cyra } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyryu } \IeC {\CYRO }\IeC {\CYRO }\IeC {\CYRP }\hskip0mm\strut & 01.11.\yeari\tablestrut& \strut\\
    \cline{1-3}
    \IeC {\CYRP }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrv }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyrp }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrm }\IeC {\cyre }\IeC {\cyrzh }\IeC {\cyru }\IeC {\cyrt }\IeC {\cyro }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyro }\IeC {\cyrt }\IeC {\cyrch }\IeC {\cyryo }\IeC {\cyrt }\hskip0mm\strut & 31.12.\yeari\tablestrut & \\
    \cline{1-3}
    \IeC {\CYRV }\IeC {\cyrt }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrp }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrm }\IeC {\cyre }\IeC {\cyrzh }\IeC {\cyru }\IeC {\cyrt }\IeC {\cyro }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyro }\IeC {\cyrt }\IeC {\cyrch }\IeC {\cyryo }\IeC {\cyrt }\hskip0mm\strut & 31.03.\yearii\tablestrut & \\
    \cline{1-3}
    \IeC {\CYRD }\IeC {\cyro }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd } \IeC {\cyrn }\IeC {\cyra } \IeC {\cyrs }\IeC {\cyrt }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrch }\IeC {\cyre }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrk }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyri }\hskip0mm\strut & 30.04.\yearii\tablestrut & \\
    \cline{1-3}
    \IeC {\CYRS }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }\IeC {\cyra } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR } \IeC {\cyrn }\IeC {\cyra }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrm }\IeC {\cyru } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyryu }\hskip0mm\strut & 15.05.\yearii\tablestrut & \\
    \cline{1-3}
    \IeC {\CYRS }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }\IeC {\cyra } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyryu } \IeC {\CYRO }\IeC {\CYRO }\IeC {\CYRP }\hskip0mm\strut & 25.05.\yearii\tablestrut & \\
    \cline{1-3}
    \end{tabu}
    
    \vskip3mm
    01.11.\yeari
    
    \vskip10mm
    \IeC {\CYRP }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrp }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrsftsn } \IeC {\cyrn }\IeC {\cyra }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyro } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrya } \hrulefill\space \briefsupervisername
    
    \vskip10mm
    \IeC {\CYRP }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrp }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrsftsn } \IeC {\cyro }\IeC {\cyrb }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyra }\IeC {\cyryu }\IeC {\cyrshch }\IeC {\cyre }\IeC {\cyrg }\IeC {\cyro }\IeC {\cyrs }\IeC {\cyrya }  \hrulefill\space \briefstudentname
    \end{minipage}%
    \hspace*{\pagesep}%
    \begin{minipage}[t]{\pagewidth}%
    \begin{center}
    {\bfseries\small \IeC {\CYRF }\IeC {\CYRG }\IeC {\CYRB }\IeC {\CYRO }\IeC {\CYRU } \IeC {\CYRV }\IeC {\CYRO } «\IeC {\CYRT }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrg }\IeC {\cyro }\IeC {\cyrs }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyru }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrt }»}
    \vskip3mm
    \hrule
    \vskip3mm
    \IeC {\CYRN }\IeC {\cyra }\IeC {\cyrp }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrv }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \csname specialityname\programname\endcsname
    
    \vskip2mm
    \IeC {\CYRO }\IeC {\CYRO }\IeC {\CYRP } <<\csname programname\programname\endcsname>>
    \end{center}
    
    \begin{flushright}
    \begin{minipage}{.5\textwidth}
    \begin{center}
    \IeC {\CYRU }\IeC {\CYRT }\IeC {\CYRV }\IeC {\CYRE }\IeC {\CYRR }\IeC {\CYRZH }\IeC {\CYRD }\IeC {\CYRA }\IeC {\CYRYU }
    
    \IeC {\CYRR }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrsftsn } \IeC {\CYRO }\IeC {\CYRO }\IeC {\CYRP }
    
    \vskip7mm
    \vrule height 0.1mm width 0.7\hsize
    \vskip1mm
    \csname headname\programname\endcsname\\
    10 \IeC {\cyrn }\IeC {\cyro }\IeC {\cyrya }\IeC {\cyrb }\IeC {\cyrr }\IeC {\cyrya } \yeari\,\IeC {\cyrg }. 
    \end{center}
    \end{minipage}
    \end{flushright}
    
    \begin{center}
    {\scshape
    \large \IeC {\CYRZ }\IeC {\CYRA }\IeC {\CYRD }\IeC {\CYRA }\IeC {\CYRN }\IeC {\CYRI }\IeC {\CYRE }
    
    \normalsize \IeC {\cyrn }\IeC {\cyra } \IeC {\cyrv }\IeC {\cyrery }\IeC {\cyrp }\IeC {\cyru }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyrn }\IeC {\cyru }\IeC {\cyryu } \IeC {\cyrk }\IeC {\cyrv }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyri }\IeC {\cyrf }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyru }\IeC {\cyryu } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyru }}
    \end{center}
    
    \raggedright
    \noindent
    \IeC {\CYRO }\IeC {\cyrb }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyra }\IeC {\cyryu }\IeC {\cyrshch }\IeC {\cyri }\IeC {\cyrishrt }\IeC {\cyrs }\IeC {\cyrya }: {\assignfont \studentname}, \IeC {\cyrg }\IeC {\cyrr }\IeC {\cyru }\IeC {\cyrp }\IeC {\cyrp }\IeC {\cyra } \groupstudentname
    
    \vskip\itemskip
    \noindent
    \IeC {\CYRN }\IeC {\cyra }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrsftsn }:
    {\assignfont \supervisername,
    \positionsupervisername%
    \ifx\degreesupervisername\emptymacro\else, \degreesupervisername\fi
    \ifx\ranksupervisername\emptymacro\else, \ranksupervisername\fi
    }
    
    \vskip\itemskip
    \noindent
    1. \IeC {\CYRT }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR }: {\assignfont <<\titlename>>}
    
    \noindent
    \IeC {\cyru }\IeC {\cyrt }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrzh }\IeC {\cyrd }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyra } \IeC {\cyrp }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }\IeC {\cyrz }\IeC {\cyro }\IeC {\cyrm } \IeC {\cyrr }\IeC {\cyre }\IeC {\cyrk }\IeC {\cyrt }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyra } \IeC {\cyro }\IeC {\cyrt } \orderdatename{} №\,\ordernumbername{}
    
    \vskip\itemskip
    \noindent
    2. \IeC {\CYRS }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrk } \IeC {\cyrs }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }\IeC {\cyri } \IeC {\cyro }\IeC {\cyrb }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyra }\IeC {\cyryu }\IeC {\cyrshch }\IeC {\cyri }\IeC {\cyrm }\IeC {\cyrs }\IeC {\cyrya } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR }: {\assignfont 25.05.\yearii}
    
    \vskip\itemskip
    \noindent
    3. \IeC {\CYRC }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrsftsn } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR }: {\assignfont \goalname}
    \end{minipage}%
    \newpage
    \noindent
    \begin{minipage}[t]{\pagewidth}%
    \raggedright
    \noindent
    4. \IeC {\CYRP }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyre }\IeC {\cyrch }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrsftsn } \IeC {\cyrz }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }, \IeC {\cyrp }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrzh }\IeC {\cyra }\IeC {\cyrshch }\IeC {\cyri }\IeC {\cyrh } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrz }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyrk }\IeC {\cyre } \IeC {\cyrv } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR }:
    \assignfont
    \begin{enumerate}
    \let\task\tasktask
    \tasksname
    \end{enumerate}
    \end{minipage}%
    \hspace*{\pagesep}%
    \begin{minipage}[t]{\pagewidth}%
    \raggedright
    \noindent
    5. \IeC {\CYRP }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyre }\IeC {\cyrch }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrsftsn } \IeC {\cyri }\IeC {\cyrl }\IeC {\cyrl }\IeC {\cyryu }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyri }\IeC {\cyrv }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyro } \IeC {\cyrm }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyra }
    {\assignfont
    \ifx\imagesname\relax\\\IeC {\CYRO }\IeC {\cyrt }\IeC {\cyrs }\IeC {\cyru }\IeC {\cyrt }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrv }\IeC {\cyru }\IeC {\cyre }\IeC {\cyrt }
    \else
        \begin{enumerate}[label=\arabic*)]
        \imagesname
        \end{enumerate}%
    \fi}
    
    \vskip\itemskip
    \noindent
    6. \IeC {\CYRK }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyrs }\IeC {\cyru }\IeC {\cyrl }\IeC {\cyrsftsn }\IeC {\cyrt }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyrt }\IeC {\cyrery } \IeC {\cyrp }\IeC {\cyro } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR } (\IeC {\cyrs } \IeC {\cyru }\IeC {\cyrk }\IeC {\cyra }\IeC {\cyrz }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre }\IeC {\cyrm } \IeC {\cyro }\IeC {\cyrt }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrs }\IeC {\cyrya }\IeC {\cyrshch }\IeC {\cyri }\IeC {\cyrh }\IeC {\cyrs }\IeC {\cyrya } \IeC {\cyrk } \IeC {\cyrn }\IeC {\cyri }\IeC {\cyrm } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrz }\IeC {\cyrd }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyro }\IeC {\cyrv } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR })
    {\assignfont
    \ifx\advisersname\relax\\\IeC {\CYRO }\IeC {\cyrt }\IeC {\cyrs }\IeC {\cyru }\IeC {\cyrt }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrv }\IeC {\cyru }\IeC {\cyryu }\IeC {\cyrt }
    \else
        \begin{enumerate}[label=\arabic*)]
        \advisersname
        \end{enumerate}%
    \fi}
    
    
    \vskip\itemskip
    \noindent
    7. \IeC {\CYRD }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyra } \IeC {\cyrv }\IeC {\cyrery }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }\IeC {\cyri } \IeC {\cyrz }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrya } 01.11.\yeari
    
    \vskip10mm
    \IeC {\CYRP }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrp }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrsftsn } \IeC {\cyrn }\IeC {\cyra }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyro } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrya } \hrulefill\space \briefsupervisername
    
    \vskip\itemskip
    \noindent
    8. \IeC {\CYRZ }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \IeC {\cyrp }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrn }\IeC {\cyrya }\IeC {\cyrl } \IeC {\cyrk } \IeC {\cyri }\IeC {\cyrs }\IeC {\cyrp }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyrn }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyryu } 01.11.\yeari
    
    \vskip10mm
    \IeC {\CYRP }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrp }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrsftsn } \IeC {\cyro }\IeC {\cyrb }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyra }\IeC {\cyryu }\IeC {\cyrshch }\IeC {\cyre }\IeC {\cyrg }\IeC {\cyro }\IeC {\cyrs }\IeC {\cyrya }  \hrulefill\space \briefstudentname
    \end{minipage}%
    }
\fi %\ifbachelor

\ifmaster
    \def\makeassignment{%
    \linespread{1.03}
    \begin{center}
    {\bfseries\small \IeC {\CYRF }\IeC {\CYRG }\IeC {\CYRB }\IeC {\CYRO }\IeC {\CYRU } \IeC {\CYRV }\IeC {\CYRO } «\IeC {\CYRT }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrg }\IeC {\cyro }\IeC {\cyrs }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyru }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrt }»}
    
    \vskip1mm
    
    {\bfseries\small \IeC {\CYRI}\IeC {\cyrn}\IeC {\cyrs}\IeC {\cyrt}\IeC {\cyri}\IeC {\cyrt}\IeC {\cyru}\IeC {\cyrt} \IeC {\cyrm}\IeC {\cyra}\IeC {\cyrt}\IeC {\cyre}\IeC {\cyrm}\IeC {\cyra}\IeC {\cyrt}\IeC {\cyri}\IeC {\cyrk}\IeC {\cyri} \IeC {\cyri} \IeC {\cyri}\IeC {\cyrn}\IeC {\cyrf}\IeC {\cyro}\IeC {\cyrr}\IeC {\cyrm}\IeC {\cyra}\IeC {\cyrc}\IeC {\cyri}\IeC {\cyro}\IeC {\cyrn}\IeC {\cyrn}\IeC {\cyrery}\IeC {\cyrh} \IeC {\cyrt}\IeC {\cyre}\IeC {\cyrh}\IeC {\cyrn}\IeC {\cyro}\IeC {\cyrl}\IeC {\cyro}\IeC {\cyrg}\IeC {\cyri}\IeC {\cyrishrt}}
    \vskip3mm
    \hrule
    \vskip3mm
    \IeC {\CYRN }\IeC {\cyra }\IeC {\cyrp }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrv }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \IeC {\cyrp }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrg }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyrk }\IeC {\cyri } \csname specialityname\programname\endcsname
    
    \vskip2mm
    \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrf }\IeC {\cyri }\IeC {\cyrl }\IeC {\cyrsftsn } <<\csname programname\programname\endcsname>>
    \end{center}
    
    \begin{flushright}
    \begin{minipage}{.5\textwidth}
    \begin{center}
    \IeC {\CYRU }\IeC {\CYRT }\IeC {\CYRV }\IeC {\CYRE }\IeC {\CYRR }\IeC {\CYRZH }\IeC {\CYRD }\IeC {\CYRA }\IeC {\CYRYU }
    
    \IeC {\CYRR }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrsftsn } \IeC {\CYRO }\IeC {\CYRO }\IeC {\CYRP }
    
    \vskip7mm
    \vrule height 0.1mm width 0.7\hsize
    \vskip1mm
    \csname headname\programname\endcsname\\
    10 \IeC {\cyrn }\IeC {\cyro }\IeC {\cyrya }\IeC {\cyrb }\IeC {\cyrr }\IeC {\cyrya } \yeari\,\IeC {\cyrg }. 
    \end{center}
    \end{minipage}
    \end{flushright}
    
    \begin{center}
    {\scshape
    \large \IeC {\CYRZ }\IeC {\CYRA }\IeC {\CYRD }\IeC {\CYRA }\IeC {\CYRN }\IeC {\CYRI }\IeC {\CYRE }
    
    \normalsize \IeC {\cyrn }\IeC {\cyra } \IeC {\cyrv }\IeC {\cyrery }\IeC {\cyrp }\IeC {\cyru }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyrn }\IeC {\cyru }\IeC {\cyryu } \IeC {\cyrk }\IeC {\cyrv }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyri }\IeC {\cyrf }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyru }\IeC {\cyryu } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyru }\\
    (\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrg }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyru }\IeC {\cyryu } \IeC {\cyrd }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrs }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrt }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyryu })}
    \end{center}
    
    \raggedright
    \noindent
    {\bfseries \IeC {\CYRO }\IeC {\cyrb }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyra }\IeC {\cyryu }\IeC {\cyrshch }\IeC {\cyri }\IeC {\cyrishrt }\IeC {\cyrs }\IeC {\cyrya }:} {\assignfont \studentname}, \IeC {\cyrg }\IeC {\cyrr }\IeC {\cyru }\IeC {\cyrp }\IeC {\cyrp }\IeC {\cyra } \groupstudentname
    
    \vskip\itemskip
    \noindent
    {\bfseries \IeC {\CYRN }\IeC {\cyra }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrsftsn }:}
    {\assignfont \supervisername,
    \positionsupervisername%
    \ifx\degreesupervisername\emptymacro\else, \degreesupervisername\fi
    \ifx\ranksupervisername\emptymacro\else, \ranksupervisername\fi
    }
    
    \vskip\itemskip
    \noindent
    {\bfseries \IeC {\CYRT }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra }:} {\assignfont <<\titlename>>}
    
    \noindent
    {\bfseries \IeC {\CYRU }\IeC {\cyrt }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrzh }\IeC {\cyrd }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyra } \IeC {\cyrp }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }\IeC {\cyrz }\IeC {\cyro }\IeC {\cyrm } \IeC {\cyrp }\IeC {\cyro } \IeC {\cyru }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrt }\IeC {\cyru }} №\,\ordernumbername{} \IeC {\cyro }\IeC {\cyrt } \orderdatename{}
    
    \vskip\itemskip
    \noindent
    {\bfseries \IeC {\CYRC }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrsftsn } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyrery }:} {\assignfont \goalname}
    
    \vskip\itemskip
    \noindent
    {\bfseries \IeC {\CYRP }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyre }\IeC {\cyrch }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrsftsn } (\IeC {\cyrp }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrm }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt }) \IeC {\cyro }\IeC {\cyrs }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrh } \IeC {\cyrz }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }, \IeC {\cyrk }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyro }\IeC {\cyrr }\IeC {\cyrery }\IeC {\cyre } \IeC {\cyrd }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyrzh }\IeC {\cyrn }\IeC {\cyrery } \IeC {\cyrb }\IeC {\cyrery }\IeC {\cyrt }\IeC {\cyrsftsn } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrs }\IeC {\cyrs }\IeC {\cyrm }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyrr }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrery } \IeC {\cyrv } \IeC {\cyrd }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrs }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrt }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyri }:}
    {\assignfont
    \begin{enumerate}
    \let\task\tasktask
    \tasksname
    \end{enumerate}
    }
    
    \noindent
    \vskip5mm
    \IeC {\CYRP }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrp }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrsftsn } \IeC {\cyrn }\IeC {\cyra }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyro } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrya } \hrulefill\space \briefsupervisername
    
    \IeC {\CYRD }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyra } \IeC {\cyrv }\IeC {\cyrery }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }\IeC {\cyri } \IeC {\cyrz }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrya } 01.11.\yeari
    
    \vskip\itemskip
    \noindent
    \IeC {\CYRZ }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \IeC {\cyrp }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrn }\IeC {\cyrya }\IeC {\cyrl } \IeC {\cyrk } \IeC {\cyri }\IeC {\cyrs }\IeC {\cyrp }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyrn }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyryu }
    
    \noindent
    \IeC {\CYRP }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrp }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrsftsn } \IeC {\cyro }\IeC {\cyrb }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyra }\IeC {\cyryu }\IeC {\cyrshch }\IeC {\cyre }\IeC {\cyrg }\IeC {\cyro }\IeC {\cyrs }\IeC {\cyrya }  \hrulefill\space \briefstudentname
    
    \newpage
    \begin{center}
    {\bfseries \IeC {\CYRK }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrr }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyrg }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrf }\IeC {\cyri }\IeC {\cyrk }}\\
    \IeC {\cyrv }\IeC {\cyrery }\IeC {\cyrp }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyrn }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrya } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR } (\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrg }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrd }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrs }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrt }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyri })
    \end{center}
    
    \noindent
    {\small {\bfseries \IeC {\CYRT }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra } \IeC {\cyrd }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrs }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrt }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyri }:} \titlename}
    
    \vskip\itemskip
    \begin{tabu}{|X[3,L]|X[1,C]|X[1,C]|}
    %\cline{1-3}
    \hline
    \IeC {\CYRV }\IeC {\cyrery }\IeC {\cyrp }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyrn }\IeC {\cyrya }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrya } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyra } & \IeC {\CYRS }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrk }\IeC {\cyri } \IeC {\cyrv }\IeC {\cyrery }\IeC {\cyrp }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyrn }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrya } & \IeC {\CYRO }\IeC {\cyrt }\IeC {\cyrm }\IeC {\cyre }\IeC {\cyrt }\IeC {\cyrk }\IeC {\cyra } \IeC {\cyro } \IeC {\cyrv }\IeC {\cyrery }\IeC {\cyrp }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyrn }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyri }\hskip0mm\strut\\
    \hline
    %\cline{1-3}
    \IeC {\CYRV }\IeC {\cyrery }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrr } \IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyrery } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR }\hskip0mm\strut & 30.10.\yeari\tablestrut& \strut\\
    \cline{1-3}
    \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyre }\IeC {\cyrd }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyra }\IeC {\cyrv }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \IeC {\cyrz }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrya } \IeC {\cyrn }\IeC {\cyra } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyryu } \IeC {\CYRO }\IeC {\CYRO }\IeC {\CYRP }\hskip0mm\strut & 01.11.\yeari\tablestrut& \strut\\
    \cline{1-3}
    \IeC {\CYRO }\IeC {\cyrt }\IeC {\cyrch }\IeC {\cyryo }\IeC {\cyrt } \IeC {\cyrp }\IeC {\cyro } \IeC {\CYRN }\IeC {\CYRI }\IeC {\CYRR }\hskip0mm\strut & 31.12.\yeari\tablestrut & \\
    \cline{1-3}
    \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrm }\IeC {\cyre }\IeC {\cyrzh }\IeC {\cyru }\IeC {\cyrt }\IeC {\cyro }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyro }\IeC {\cyrt }\IeC {\cyrch }\IeC {\cyryo }\IeC {\cyrt }\hskip0mm\strut & 31.03.\yearii\tablestrut & \\
    \cline{1-3}
    \IeC {\CYRD }\IeC {\cyro }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrd } \IeC {\cyrn }\IeC {\cyra } \IeC {\cyrk }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyrf }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyri }\hskip0mm\strut & 30.04.\yearii\tablestrut & \\
    \cline{1-3}
    \IeC {\CYRS }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }\IeC {\cyra } \IeC {\cyrn }\IeC {\cyra }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrp }\IeC {\cyru }\IeC {\cyrb }\IeC {\cyrl }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyri } \IeC {\cyrv } \IeC {\cyrp }\IeC {\cyre }\IeC {\cyrch }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyrsftsn }\hskip0mm\strut & 12.05.\yearii\tablestrut & \\
    \cline{1-3}
    \IeC {\CYRS }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }\IeC {\cyra } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR } \IeC {\cyrn }\IeC {\cyra }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrm }\IeC {\cyru } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyryu }\hskip0mm\strut & 18.05.\yearii\tablestrut & \\
    \cline{1-3}
    \IeC {\CYRS }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }\IeC {\cyra } \IeC {\CYRV }\IeC {\CYRK }\IeC {\CYRR } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyryu } \IeC {\CYRO }\IeC {\CYRO }\IeC {\CYRP }\hskip0mm\strut & 25.05.\yearii\tablestrut & \\
    \cline{1-3}
    \end{tabu}
    
    \vskip3mm
    \IeC {\CYRD }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyra } \hfill 01.11.\yeari
    
    \vskip10mm
    \IeC {\CYRP }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrp }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrsftsn } \IeC {\cyrn }\IeC {\cyra }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyro } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrya } \hrulefill\space \briefsupervisername
    
    \vskip10mm
    \IeC {\CYRP }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrp }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrsftsn } \IeC {\cyro }\IeC {\cyrb }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyra }\IeC {\cyryu }\IeC {\cyrshch }\IeC {\cyre }\IeC {\cyrg }\IeC {\cyro }\IeC {\cyrs }\IeC {\cyrya }  \hrulefill\space \briefstudentname
    }
\fi %\ifmaster

\iftermpaper
    \def\makeassignment{%
    \linespread{1.03}
    \noindent
    \begin{minipage}[t]{\pagewidth}%
    ~
    \end{minipage}%
    \hspace*{\pagesep}%
    \begin{minipage}[t]{\pagewidth}%
    \begin{center}
    {\bfseries\small \IeC {\CYRF }\IeC {\CYRG }\IeC {\CYRB }\IeC {\CYRO }\IeC {\CYRU } \IeC {\CYRV }\IeC {\CYRO } «\IeC {\CYRT }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrg }\IeC {\cyro }\IeC {\cyrs }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyru }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrt }»}
    \vskip3mm
    \hrule
    \vskip3mm
    \IeC {\CYRN }\IeC {\cyra }\IeC {\cyrp }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrv }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \csname specialityname\programname\endcsname
    
    \vskip2mm
    \IeC {\CYRO }\IeC {\CYRO }\IeC {\CYRP } <<\csname programname\programname\endcsname>>
    \end{center}
    
    \begin{flushright}
    \begin{minipage}{.5\textwidth}
    \begin{center}
    \IeC {\CYRU }\IeC {\CYRT }\IeC {\CYRV }\IeC {\CYRE }\IeC {\CYRR }\IeC {\CYRZH }\IeC {\CYRD }\IeC {\CYRA }\IeC {\CYRYU }
    
    \IeC {\CYRR }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrsftsn } \IeC {\CYRO }\IeC {\CYRO }\IeC {\CYRP }
    
    \vskip7mm
    \vrule height 0.1mm width 0.7\hsize
    \vskip1mm
    \csname headname\programname\endcsname\\
    01 \IeC {\cyrn }\IeC {\cyro }\IeC {\cyrya }\IeC {\cyrb }\IeC {\cyrr }\IeC {\cyrya } \yeari\,\IeC {\cyrg }. 
    \end{center}
    \end{minipage}
    \end{flushright}
    
    \begin{center}
    {\scshape
    \large \IeC {\CYRZ }\IeC {\CYRA }\IeC {\CYRD }\IeC {\CYRA }\IeC {\CYRN }\IeC {\CYRI }\IeC {\CYRE }
    
    \normalsize \IeC {\cyrn }\IeC {\cyra } \IeC {\cyrk }\IeC {\cyru }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyru }\IeC {\cyryu } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyru }\\
    \IeC {\cyrp }\IeC {\cyro } \IeC {\cyrd }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyrp }\IeC {\cyrl }\IeC {\cyri }\IeC {\cyrn }\IeC {\cyre } <<\subjectname>>
    }
    \end{center}
    
    \raggedright
    \noindent
    \IeC {\CYRO }\IeC {\cyrb }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyra }\IeC {\cyryu }\IeC {\cyrshch }\IeC {\cyri }\IeC {\cyrishrt }\IeC {\cyrs }\IeC {\cyrya }: {\assignfont \studentname}, \IeC {\cyrg }\IeC {\cyrr }\IeC {\cyru }\IeC {\cyrp }\IeC {\cyrp }\IeC {\cyra } \groupstudentname
    
    \vskip\itemskip
    \noindent
    \IeC {\CYRN }\IeC {\cyra }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrsftsn }:
    {\assignfont \supervisername,
    \positionsupervisername%
    \ifx\degreesupervisername\emptymacro\else, \degreesupervisername\fi
    \ifx\ranksupervisername\emptymacro\else, \ranksupervisername\fi
    }
    
    \vskip\itemskip
    \noindent
    1. \IeC {\CYRT }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra } \IeC {\cyrk }\IeC {\cyru }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyrery }: {\assignfont <<\titlename>>}
    
    \vskip\itemskip
    \noindent
    2. \IeC {\CYRS }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrk } \IeC {\cyrs }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }\IeC {\cyri } \IeC {\cyrk }\IeC {\cyru }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyrery }: {\assignfont 25.05.\yearii}
    
    \vskip\itemskip
    \noindent
    3. \IeC {\CYRC }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrsftsn } \IeC {\cyrk }\IeC {\cyru }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyrery }: {\assignfont \goalname}
    \end{minipage}%
    \newpage
    \noindent
    \begin{minipage}[t]{\pagewidth}%
    \raggedright
    \noindent
    4. \IeC {\CYRP }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyre }\IeC {\cyrch }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrsftsn } \IeC {\cyrz }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }, \IeC {\cyrp }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrzh }\IeC {\cyra }\IeC {\cyrshch }\IeC {\cyri }\IeC {\cyrh } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrz }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyrk }\IeC {\cyre } \IeC {\cyrv } \IeC {\cyrk }\IeC {\cyru }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyre }:
    {\assignfont
    \begin{enumerate}
    \let\task\tasktask
    \tasksname
    \end{enumerate}
    }
    
    \vskip\itemskip
    \noindent
    5. \IeC {\CYRD }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyra } \IeC {\cyrv }\IeC {\cyrery }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }\IeC {\cyri } \IeC {\cyrz }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrya } 31.10.\yeari
    
    \vskip10mm
    \IeC {\CYRP }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrp }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrsftsn } \IeC {\cyrn }\IeC {\cyra }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrg }\IeC {\cyro } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrya } \hrulefill\space \briefsupervisername
    
    \vskip\itemskip
    \noindent
    6. \IeC {\CYRZ }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \IeC {\cyrp }\IeC {\cyrr }\IeC {\cyri }\IeC {\cyrn }\IeC {\cyrya }\IeC {\cyrl } \IeC {\cyrk } \IeC {\cyri }\IeC {\cyrs }\IeC {\cyrp }\IeC {\cyro }\IeC {\cyrl }\IeC {\cyrn }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyryu } 31.10.\yeari
    
    \vskip10mm
    \IeC {\CYRP }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrp }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrsftsn } \IeC {\cyro }\IeC {\cyrb }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyra }\IeC {\cyryu }\IeC {\cyrshch }\IeC {\cyre }\IeC {\cyrg }\IeC {\cyro }\IeC {\cyrs }\IeC {\cyrya }  \hrulefill\space \briefstudentname
    \end{minipage}%
    \hspace*{\pagesep}%
    \begin{minipage}[t]{\pagewidth}%
    \end{minipage}%
    }
\fi %\iftermpaper

\ifnotassign

    \ifessay
        \def\introduction{%
            \oldsection*{\IeC {\CYRV }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrd }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre }%
            \phantomsection
            \addcontentsline{toc}{section}{\IeC {\CYRV }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrd }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre }}%
            }%
            }
        \def\conclusion{%
        	\oldsection*{\IeC {\CYRZ }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyryu }\IeC {\cyrch }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre }
        	}%
            \phantomsection
            \addcontentsline{toc}{section}{\IeC {\CYRZ }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyryu }\IeC {\cyrch }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre }}%
            }
    \else
        \def\introduction{%
            \chapter*{\IeC {\CYRV }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrd }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre }%
            \phantomsection
            \addcontentsline{toc}{chapter}{\IeC {\CYRV }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrd }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre }}%
            }%
            }
        \def\actuality{%
            %\phantomsection
            %\addcontentsline{toc}{section}{\IeC {\CYRA }\IeC {\cyrk }\IeC {\cyrt }\IeC {\cyru }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyrsftsn }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrsftsn }}%
            \oldsection*{\IeC {\CYRA }\IeC {\cyrk }\IeC {\cyrt }\IeC {\cyru }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyrsftsn }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrsftsn }}}
        \def\review{%
            %\phantomsection
            %\addcontentsline{toc}{section}{\IeC {\CYRO }\IeC {\cyrb }\IeC {\cyrz }\IeC {\cyro }\IeC {\cyrr } \IeC {\cyrl }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyru }\IeC {\cyrr }\IeC {\cyrery }}%
            \oldsection*{\IeC {\CYRO }\IeC {\cyrb }\IeC {\cyrz }\IeC {\cyro }\IeC {\cyrr } \IeC {\cyrl }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyru }\IeC {\cyrr }\IeC {\cyrery }}}
        \def\goalandtasks{%
            %\phantomsection
            %\addcontentsline{toc}{section}{\IeC {\CYRC }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyri } \IeC {\cyri } \IeC {\cyrz }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }\IeC {\cyri }}%
            \oldsection*{\IeC {\CYRC }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrsftsn } \IeC {\cyri } \IeC {\cyrz }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }\IeC {\cyri }}
            \paragraph*{\IeC {\CYRC }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrsftsn } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyrery }.}
            \goalname
            \paragraph*{\IeC {\CYRZ }\IeC {\cyra }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrch }\IeC {\cyri }}
            \begin{enumerate}
            \let\task\tasktask
            \tasksname
            \end{enumerate}
            }
        \def\tools{%
            %\phantomsection
            %\addcontentsline{toc}{section}{\IeC {\CYRM }\IeC {\cyre }\IeC {\cyrt }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrery } \IeC {\cyri } \IeC {\cyrs }\IeC {\cyrr }\IeC {\cyre }\IeC {\cyrd }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrv }\IeC {\cyra }}%
            \oldsection*{\IeC {\CYRM }\IeC {\cyre }\IeC {\cyrt }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrery } \IeC {\cyri } \IeC {\cyrs }\IeC {\cyrr }\IeC {\cyre }\IeC {\cyrd }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrv }\IeC {\cyra }}}
        \def\results{%
            %\phantomsection
            %\addcontentsline{toc}{section}{\IeC {\CYRO }\IeC {\cyrs }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyre } \IeC {\cyrr }\IeC {\cyre }\IeC {\cyrz }\IeC {\cyru }\IeC {\cyrl }\IeC {\cyrsftsn }\IeC {\cyrt }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyrery }}%
            \oldsection*{\IeC {\CYRO }\IeC {\cyrs }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyre } \IeC {\cyrr }\IeC {\cyre }\IeC {\cyrz }\IeC {\cyru }\IeC {\cyrl }\IeC {\cyrsftsn }\IeC {\cyrt }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyrery }}
            \begin{enumerate}
            \let\task\taskresult
            \tasksname
            \end{enumerate}
            }
        \def\originality{%
            %\phantomsection
            %\addcontentsline{toc}{section}{\IeC {\CYRN }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyri }\IeC {\cyrz }\IeC {\cyrn }\IeC {\cyra }}%
            \oldsection*{\IeC {\CYRN }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyri }\IeC {\cyrz }\IeC {\cyrn }\IeC {\cyra }}}
        \def\approbation{%
            %\phantomsection
            %\addcontentsline{toc}{section}{\IeC {\CYRA }\IeC {\cyrp }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrb }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyrya }}%
            \oldsection*{\IeC {\CYRA }\IeC {\cyrp }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrb }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyrya }}}
        \def\structure{%
            %\phantomsection
            %\addcontentsline{toc}{section}{\IeC {\CYRS }\IeC {\cyrt }\IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyrt }\IeC {\cyru }\IeC {\cyrr }\IeC {\cyra } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyrery }}%
            \oldsection*{\IeC {\CYRS }\IeC {\cyrt }\IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyrt }\IeC {\cyru }\IeC {\cyrr }\IeC {\cyra } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyrery }}}
        \def\conclusion{%
            \chapter*{\IeC {\CYRZ }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyryu }\IeC {\cyrch }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre }
            \phantomsection
            \addcontentsline{toc}{chapter}{\IeC {\CYRZ }\IeC {\cyra }\IeC {\cyrk }\IeC {\cyrl }\IeC {\cyryu }\IeC {\cyrch }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre }}%
            }%
            }
    \fi %\ifessay
    
    \def\maketitlepage{%
        \thispagestyle{empty}
        \begin{center}
        \IeC {\CYRM }\IeC {\CYRI }\IeC {\CYRN }\IeC {\CYRI }\IeC {\CYRS }\IeC {\CYRT }\IeC {\CYRE }\IeC {\CYRR }\IeC {\CYRS }\IeC {\CYRT }\IeC {\CYRV }\IeC {\CYRO } \IeC {\CYRN }\IeC {\CYRA }\IeC {\CYRU }\IeC {\CYRK }\IeC {\CYRI } \IeC {\CYRI } \IeC {\CYRV }\IeC {\CYRERY }\IeC {\CYRS }\IeC {\CYRSH }\IeC {\CYRE }\IeC {\CYRG }\IeC {\CYRO } \IeC {\CYRO }\IeC {\CYRB }\IeC {\CYRR }\IeC {\CYRA }\IeC {\CYRZ }\IeC {\CYRO }\IeC {\CYRV }\IeC {\CYRA }\IeC {\CYRN }\IeC {\CYRI }\IeC {\CYRYA } \IeC {\CYRR }\IeC {\CYRF }
        
        \vskip0.5ex
        \IeC {\CYRF }\IeC {\cyre }\IeC {\cyrd }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyrsftsn }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyre } \IeC {\cyrg }\IeC {\cyro }\IeC {\cyrs }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyre } \IeC {\cyrb }\IeC {\cyryu }\IeC {\cyrd }\IeC {\cyrzh }\IeC {\cyre }\IeC {\cyrt }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyre }\\
        \IeC {\cyro }\IeC {\cyrb }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrz }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyra }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrsftsn }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyre } \IeC {\cyru }\IeC {\cyrch }\IeC {\cyrr }\IeC {\cyre }\IeC {\cyrzh }\IeC {\cyrd }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \IeC {\cyrv }\IeC {\cyrery }\IeC {\cyrs }\IeC {\cyrsh }\IeC {\cyre }\IeC {\cyrg }\IeC {\cyro } \IeC {\cyro }\IeC {\cyrb }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrz }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyra }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrya }\\
        <<\IeC {\CYRT }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrg }\IeC {\cyro }\IeC {\cyrs }\IeC {\cyru }\IeC {\cyrd }\IeC {\cyra }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyru }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrt }>>
        
        \vskip1.5ex
        \hrule
        
        \vskip1.5ex
        \IeC {\CYRI}\IeC {\cyrn}\IeC {\cyrs}\IeC {\cyrt}\IeC {\cyri}\IeC {\cyrt}\IeC {\cyru}\IeC {\cyrt} \IeC {\cyrm}\IeC {\cyra}\IeC {\cyrt}\IeC {\cyre}\IeC {\cyrm}\IeC {\cyra}\IeC {\cyrt}\IeC {\cyri}\IeC {\cyrk}\IeC {\cyri} \IeC {\cyri} \IeC {\cyri}\IeC {\cyrn}\IeC {\cyrf}\IeC {\cyro}\IeC {\cyrr}\IeC {\cyrm}\IeC {\cyra}\IeC {\cyrc}\IeC {\cyri}\IeC {\cyro}\IeC {\cyrn}\IeC {\cyrn}\IeC {\cyrery}\IeC {\cyrh} \IeC {\cyrt}\IeC {\cyre}\IeC {\cyrh}\IeC {\cyrn}\IeC {\cyro}\IeC {\cyrl}\IeC {\cyro}\IeC {\cyrg}\IeC {\cyri}\IeC {\cyrishrt}
        
        \vskip1.5ex
        \IeC {\CYRN }\IeC {\cyra }\IeC {\cyrp }\IeC {\cyrr }\IeC {\cyra }\IeC {\cyrv }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre } \csname specialityname\programname\endcsname
        
        \vskip1.5ex
        \IeC {\CYRP }\IeC {\cyrr }\IeC {\cyro }\IeC {\cyrf }\IeC {\cyri }\IeC {\cyrl }\IeC {\cyrsftsn } <<\csname programname\programname\endcsname>>
        
        \vfill
        {\large{\bfseries
        \ifsummary
            \IeC {\CYRA }\IeC {\CYRV }\IeC {\CYRT }\IeC {\CYRO }\IeC {\CYRR }\IeC {\CYRE }\IeC {\CYRF }\IeC {\CYRE }\IeC {\CYRR }\IeC {\CYRA }\IeC {\CYRT }\\
            \mdseries \IeC {\cyrv }\IeC {\cyrery }\IeC {\cyrp }\IeC {\cyru }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrk }\IeC {\cyrv }\IeC {\cyra }\IeC {\cyrl }\IeC {\cyri }\IeC {\cyrf }\IeC {\cyri }\IeC {\cyrk }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyro }\IeC {\cyrn }\IeC {\cyrn }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrr }\IeC {\cyra }\IeC {\cyrb }\IeC {\cyro }\IeC {\cyrt }\IeC {\cyrery }\\
            (\IeC {\cyrm }\IeC {\cyra }\IeC {\cyrg }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrs }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrishrt } \IeC {\cyrd }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrs }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrt }\IeC {\cyra }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyri })
        \else
            \iftermpaper
                \IeC {\CYRK }\IeC {\CYRU }\IeC {\CYRR }\IeC {\CYRS }\IeC {\CYRO }\IeC {\CYRV }\IeC {\CYRA }\IeC {\CYRYA } \IeC {\CYRR }\IeC {\CYRA }\IeC {\CYRB }\IeC {\CYRO }\IeC {\CYRT }\IeC {\CYRA }%
            \else
                \ifessay
                    \IeC {\CYRR }\IeC {\CYRE }\IeC {\CYRF }\IeC {\CYRE }\IeC {\CYRR }\IeC {\CYRA }\IeC {\CYRT }%
                \else
                    \IeC {\CYRV }\IeC {\CYRERY }\IeC {\CYRP }\IeC {\CYRU }\IeC {\CYRS }\IeC {\CYRK }\IeC {\CYRN }\IeC {\CYRA }\IeC {\CYRYA } \IeC {\CYRK }\IeC {\CYRV }\IeC {\CYRA }\IeC {\CYRL }\IeC {\CYRI }\IeC {\CYRF }\IeC {\CYRI }\IeC {\CYRK }\IeC {\CYRA }\IeC {\CYRC }\IeC {\CYRI }\IeC {\CYRO }\IeC {\CYRN }\IeC {\CYRN }\IeC {\CYRA }\IeC {\CYRYA } \IeC {\CYRR }\IeC {\CYRA }\IeC {\CYRB }\IeC {\CYRO }\IeC {\CYRT }\IeC {\CYRA }%
                \fi %\ifessay
            \fi %\iftermpaper
        \fi %\ifsummary
        }

        \ifpaper
            \vskip.5ex
            {\bfseries
            \ifmaster
                (\IeC {\CYRM }\IeC {\CYRA }\IeC {\CYRG }\IeC {\CYRI }\IeC {\CYRS }\IeC {\CYRT }\IeC {\CYRE }\IeC {\CYRR }\IeC {\CYRS }\IeC {\CYRK }\IeC {\CYRA }\IeC {\CYRYA } \IeC {\CYRD }\IeC {\CYRI }\IeC {\CYRS }\IeC {\CYRS }\IeC {\CYRE }\IeC {\CYRR }\IeC {\CYRT }\IeC {\CYRA }\IeC {\CYRC }\IeC {\CYRI }\IeC {\CYRYA })%
            \else
                \ifbachelor
                    (\IeC {\CYRV }\IeC {\CYRERY }\IeC {\CYRP }\IeC {\CYRU }\IeC {\CYRS }\IeC {\CYRK }\IeC {\CYRN }\IeC {\CYRA }\IeC {\CYRYA } \IeC {\CYRR }\IeC {\CYRA }\IeC {\CYRB }\IeC {\CYRO }\IeC {\CYRT }\IeC {\CYRA } \IeC {\CYRB }\IeC {\CYRA }\IeC {\CYRK }\IeC {\CYRA }\IeC {\CYRL }\IeC {\CYRA }\IeC {\CYRV }\IeC {\CYRR }\IeC {\CYRA })%
                \else
                    {\mdseries \IeC {\cyrp }\IeC {\cyro } \IeC {\cyrd }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrc }\IeC {\cyri }\IeC {\cyrp }\IeC {\cyrl }\IeC {\cyri }\IeC {\cyrn }\IeC {\cyre }} <<\subjectname>>%
                \fi %\ifbachelor
            \fi %\ifmaster
            }
        \fi %\ifpaper
        
        \vskip1.5ex
        \ifpaper
            \Large
        \else
            \large
        \fi
        \IeC {\cyrt }\IeC {\cyre }\IeC {\cyrm }\IeC {\cyra }: {\bfseries
        <<\titlename>>\par}}
        \end{center}
        
        \vfill
        \noindent
        \begin{minipage}[b]{.4\textwidth}
        \iftermpaper\else\ifessay\else\ifsummary\else
            \small
            \begin{center}
            \IeC {\CYRD }\IeC {\CYRO }\IeC {\CYRP }\IeC {\CYRU }\IeC {\CYRSHCH }\IeC {\CYRE }\IeC {\CYRN } \IeC {\CYRK } \IeC {\CYRZ }\IeC {\CYRA }\IeC {\CYRSHCH }\IeC {\CYRI }\IeC {\CYRT }\IeC {\CYRE }
            
            \IeC {\CYRR }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrsftsn } \IeC {\CYRO }\IeC {\CYRO }\IeC {\CYRP }
            
            \vskip7mm
            \vrule height 0.1mm width 0.7\hsize
            \vskip1mm
            \csname headname\programname\endcsname
            
            \vskip5mm
            <<\uspace{10mm}>> \uspace{30mm} 20\uspace{10mm} \IeC {\cyrg }. 
            \end{center}
        \fi\fi\fi
        \end{minipage}%
        \hfill
        \begin{minipage}[b]{.4\textwidth}
        \raggedright
        {\bfseries \IeC {\CYRA }\IeC {\cyrv }\IeC {\cyrt }\IeC {\cyro }\IeC {\cyrr }:}\\
        \studentname

        \ifpaper
            \vskip5mm
            \IeC {\CYRP }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrp }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrsftsn } \uspace{30mm}
        \fi
        
        \vskip4ex
        {\bfseries \IeC {\CYRN }\IeC {\cyra }\IeC {\cyru }\IeC {\cyrch }\IeC {\cyrn }\IeC {\cyrery }\IeC {\cyrishrt } \IeC {\cyrr }\IeC {\cyru }\IeC {\cyrk }\IeC {\cyro }\IeC {\cyrv }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyri }\IeC {\cyrt }\IeC {\cyre }\IeC {\cyrl }\IeC {\cyrsftsn }:}\\
        {\supervisername%
        \ifx\degreesupervisername\emptymacro\else, \degreesupervisername\fi
        \ifx\ranksupervisername\emptymacro\else, \ranksupervisername\fi
        }

        \ifpaper
            \vskip5mm
            \IeC {\CYRP }\IeC {\cyro }\IeC {\cyrd }\IeC {\cyrp }\IeC {\cyri }\IeC {\cyrs }\IeC {\cyrsftsn } \uspace{30mm}
        \fi
        \end{minipage}
        
        \vfill
        \begin{center}
        \IeC {\CYRT }\IeC {\cyrv }\IeC {\cyre }\IeC {\cyrr }\IeC {\cyrsftsn }\,---\,\yearii
        \end{center}
        \newpage
        \pagestyle{fancy}
        \iftermpaper\else\ifessay\else\ifpaper
            \ifx\englishabstractname\relax
                \error{There is no english abstract}
            \fi
            \begingroup
            \selectlanguage{english}%
            \begin{center}%
            \Large
            {\bfseries Abstract}
            
            \Large
            \mdseries
            \englishtitlename
            
            by
            
            \Large
            \englishstudentname
            \end{center}
            
            \vskip2ex
            \englishabstractname
            \selectlanguage{russian}
            \endgroup
            \newpage
        \fi\fi\fi
        \ifpaper
            \def\contentsname{\IeC {\CYRO }\IeC {\cyrg }\IeC {\cyrl }\IeC {\cyra }\IeC {\cyrv }\IeC {\cyrl }\IeC {\cyre }\IeC {\cyrn }\IeC {\cyri }\IeC {\cyre }}
            \begingroup\raggedright\tableofcontents\endgroup
            \ifessay
                \clearpage
            \fi %\ifessay
        \fi %\ifpaper
        }%of \maketitlepage
    
\fi %\ifnotassign

"""
skill_vocab.py
Hand-curated canonical-skill -> alias map, seeded for a full-stack /
Junior Full Stack Developer Intern role (matches the sample JD:
TechNova Solutions). Extend this dict as you inspect the actual sample
JD/resumes provided at the hackathon -- that's expected and encouraged;
judges will ask how you built it.

Keys are canonical skill names (used in output/explanations).
Values are the surface forms that should count as a match, including
common misspellings/variants seen on real resumes.
"""

SKILL_VOCAB = {
    # --- Languages ---
    "javascript": ["javascript", "js", "es6", "ecmascript"],
    "typescript": ["typescript", "ts"],
    "python": ["python", "py"],
    "java": ["java"],
    "html": ["html", "html5"],
    "css": ["css", "css3"],
    "sql": ["sql", "mysql", "postgresql", "postgres", "sqlite"],

    # --- Frontend ---
    "react": ["react", "reactjs", "react.js", "react js"],
    "redux": ["redux", "redux toolkit"],
    "nextjs": ["next.js", "nextjs", "next js"],
    "vue": ["vue", "vuejs", "vue.js"],
    "angular": ["angular", "angularjs"],
    "tailwind": ["tailwind", "tailwindcss", "tailwind css"],
    "bootstrap": ["bootstrap"],

    # --- Backend ---
    "nodejs": ["node", "nodejs", "node.js", "node js"],
    "express": ["express", "express.js", "expressjs"],
    "django": ["django"],
    "flask": ["flask"],
    "fastapi": ["fastapi", "fast api"],
    "spring": ["spring", "spring boot", "springboot"],
    "rest_api": ["rest api", "restful", "rest apis", "api development", "web api"],
    "graphql": ["graphql"],

    # --- Databases ---
    "mongodb": ["mongodb", "mongo"],
    "postgresql": ["postgresql", "postgres"],
    "mysql": ["mysql"],
    "firebase": ["firebase", "firestore"],
    "redis": ["redis"],

    # --- DevOps / Tools ---
    "git": ["git", "github", "gitlab", "version control"],
    "docker": ["docker", "containerization"],
    "aws": ["aws", "amazon web services", "ec2", "s3"],
    "ci_cd": ["ci/cd", "ci cd", "continuous integration", "continuous deployment", "jenkins"],
    "linux": ["linux", "unix", "bash", "shell scripting"],

    # --- Testing ---
    "testing": ["unit testing", "jest", "mocha", "pytest", "junit", "test driven", "tdd"],

    # --- Other full-stack ecosystem terms ---
    "npm": ["npm", "yarn", "package manager"],
    "webpack": ["webpack", "vite", "bundler"],
    "microservices": ["microservices", "microservice architecture"],
    "agile": ["agile", "scrum", "kanban", "jira"],
    "responsive_design": ["responsive design", "mobile-first", "cross-browser"],
}


def all_canonical_skills():
    return list(SKILL_VOCAB.keys())


# Skills that commonly co-occur with / imply a canonical skill, but are NOT
# direct evidence of it. These must never be treated as a direct alias match
# in extraction.py -- they exist only as optional supporting context (e.g.
# for bias_check.py's "narrow tool requirement" heuristic, or for a human
# reading the report). A candidate who only has "express" does not thereby
# get credited with "node.js" as a *matched* skill.
RELATED_SKILLS = {
    "express": ["nodejs", "rest_api"],
    "react": ["javascript", "typescript"],
    "mongodb": ["nodejs", "sql"],
    "nodejs": ["express", "javascript"],
    "django": ["python", "sql"],
    "flask": ["python", "rest_api"],
    "fastapi": ["python", "rest_api"],
    "aws": ["docker", "ci_cd"],
    "docker": ["ci_cd", "aws"],
}

# Groups of tools/frameworks considered interchangeable equivalents for the
# purpose of bias_check.py's "narrow tooling requirement" heuristic (a JD
# that hard-requires exactly one member of a group, with no "or equivalent"
# language, may be unnecessarily excluding candidates who know a sibling
# tool that would do the job just as well).
EQUIVALENT_TOOL_GROUPS = [
    {"react", "vue", "angular"},
    {"mongodb", "postgresql", "mysql"},
    {"express", "django", "flask", "fastapi", "spring"},
]

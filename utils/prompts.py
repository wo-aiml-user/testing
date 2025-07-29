from langchain.prompts import PromptTemplate

summary_prompt = PromptTemplate(
    input_variables=["parsed_data", "user_feedback"],
    template="""
You are an expert AI Project Analyst. Your first task is to analyze initial project information and provide a summary to confirm your core understanding with the user before any detailed work begins.

The user has provided the following source material. This could be a detailed document or a brief, conversational idea. Adapt your analysis accordingly.

<context>
{parsed_data}
</context>

<user_feedback>
{user_feedback}
</user_feedback>

## Core Responsibilities:
-   Analyze the provided context to grasp the document's central theme and primary objective.
-   Synthesize this understanding into a very brief and executive summary.
-   If feedback is present, integrate it to improve the summary.
-   Focus only on the absolute core purpose of the document.
-   **Uncertainty Protocol:** If the context is too ambiguous or insufficient to form a coherent summary, explicitly state that you need more clarification on the document's main purpose before you can proceed.
-   Formulate natural follow-up questions to confirm your interpretation and ask for permission to proceed.

## Output Requirements:
- Your entire output MUST be a single, valid JSON object that strictly adheres to the schema provided below.
- Do not include any introductory text, explanations, or markdown formatting.

## JSON SCHEMA ##
{{{{ 
  "summary": "Concise one-paragraph explanation of the document's core purpose.",
  "follow_up_question": "natural questions to confirm your understanding and ask for permission to proceed."
}}}}
"""
)


overview_prompt = PromptTemplate(
    input_variables=["parsed_data", "user_feedback", "approved_summary"], 
    template="""
You are an Expert Project Synthesizer. Your task is to expand upon an approved summary by drawing more detail from the original source material to produce a clear project overview.

A summary has already been approved by the user. Your job is to elaborate on it.

<approved_summary>
{approved_summary}
</approved_summary>

<context>
{parsed_data}
</context>

<user_feedback>
{user_feedback}
</user_feedback>

## Core Responsibilities:
-   Understand the project’s purpose, scope, and goals by analyzing the provided context AND the approved summary.
-   Elaborate on the approved summary to create a clear, one-paragraph project overview using simple, non-technical language.
-   Integrate any feedback provided by the user to improve this detailed overview.
-   **Uncertainty Protocol:** If the context lacks the necessary details to build upon the summary, state this clearly and ask specific questions to gather the missing information.
-   Formulate one or two thoughtful follow-up questions at the end.

## Instructions:
1.  Use the approved summary as your starting point and guiding star.
2.  Expand on the summary with relevant details from the main context.
3.  Keep the final overview to a only one single, easy-to-read paragraph.
4.  Adjust the overview if feedback is present.
5.  End with natural, relevant follow-up questions.

## Output Requirements:
- Your entire output MUST be a single, valid JSON object that strictly adheres to the schema provided below.
- Do not include any introductory text, explanations, or markdown formatting.

## JSON SCHEMA ##
{{{{ 
  "overview": "Expanded one-paragraph description of the project based on approved summary and context.",
  "follow_up_question": "Natural questions for clarification or next steps."
}}}}
"""
)

feature_suggestion_prompt = PromptTemplate(
    input_variables=["parsed_data", "user_feedback", "approved_summary"],
    template="""
You are a Senior Product Strategist and Feature Consultant. Your role is to review the project's initial information and approved summary to suggest clear, realistic features that support the project’s success.

<context>
{parsed_data}
</context>

<approved_summary>
{approved_summary}
</approved_summary>

<user_feedback>
{user_feedback}
</user_feedback>

## Your Responsibilities:
-   Analyze the context and summary carefully to extract functional and strategic needs.
-   Suggest helpful features that align with business goals and user expectations.
-   Consider any feedback the user has provided to refine your feature suggestions.
-   **Uncertainty Protocol:** If the context or summary lacks clarity for feature generation, explicitly state this and ask for specific details about user goals or business objectives before providing a list.
-   Formulate a natural follow-up question at the end, asking if the user agrees or would like to make changes.

## Internal Reasoning (Before Suggesting - Do Not Output):
1.  **Analyze Goal:** What is the core purpose of the project based on the summary and context?
2.  **Incorporate Feedback:** How does the user's latest feedback shape the feature requirements? Does it add, remove, or modify a need?
3.  **Identify Gaps:** What functional gaps exist between the goal and the current information? Where can I add value?
4.  **Formulate Features:** Based on the above, what are the most critical features to suggest?

Suggested Features
-   Provide a concise, on-point list of features.
-   Each feature should be a bullet point with a brief explanation of its functionality.
-   Ask a natural, context-aware question to check if the user is happy with the suggestions or wants to refine them before moving to tech stack planning.

## Output Requirements:
- Your entire output MUST be a single, valid JSON object that strictly adheres to the schema provided below.
- Do not include any introductory text, explanations, or markdown formatting like ```json before or after the JSON object.

## JSON SCHEMA ##
{{{{ 
  "features": [
    "A concise, one-sentence description of the first suggested feature.",
    "A concise, one-sentence description of the second suggested feature.",
    "And so on for all other features..."
  ],
  "follow_up_question": "A question to confirm or refine the features before continuing."
}}}}
"""
)

tech_stack_prompt = PromptTemplate(
    input_variables=["parsed_data", "user_feedback", "approved_summary", "approved_features"],
    template="""
You are a Senior Technical Architect. Your task is to review the project's needs and recommend a practical, modern technology stack as a concise, scannable list.

<context>
{parsed_data}
</context>

<approved_summary>
{approved_summary}
</approved_summary>

<approved_features>
{approved_features}
</approved_features>

<user_feedback>
{user_feedback}
</user_feedback>

## Your Role and Core Responsibilities:
-   Understand the project's technical needs based on all provided inputs.
-   Suggest a realistic and efficient technology stack.
-   Your primary goal is to produce a scannable list. Avoid descriptive paragraphs and lengthy explanations.
-   Adapt your recommendations based on user feedback.
-   **Uncertainty Protocol:** If information is insufficient to recommend a technology, state "Information Required" for that category and list the questions needed to proceed.

## Internal Reasoning (Before Suggesting - Do Not Output):
1.  **Synthesize Requirements:** What are the key technical demands implied by the features (e.g., real-time, data-heavy, AI/ML)?
2.  **Evaluate Feedback & Constraints:** Does user feedback or context suggest platform preferences or constraints?
3.  **Formulate Recommendations:** Construct a coherent and direct list of technologies organized under the required headings.

## Technology Stack Suggestion Format:
Use `-` bullets under each heading. Do **not** use numbered or nested lists. No inline explanations.

Frontend Technologies
- [React, Next.js, etc.]

Backend Technologies
- [Python, FastAPI, REST, etc.]

Database Solutions
- [Supabase, PostgreSQL, Redis, etc.]

AI/ML Tools and Frameworks (if applicable)
- [VisionKit SDK, TensorFlow, OpenCV, etc.]

Deployment/Cloud Services
- [AWS Lambda, CloudFront, Docker, etc.]

Testing & DevOps Tools
- [Jest, Playwright, Bitbucket Pipelines, etc.]

## Output Requirements:
- Your entire output MUST be a single, valid JSON object that strictly adheres to the schema below.
- Do not include any introductory text, explanations, or markdown formatting like ```json before or after the JSON object.

## JSON SCHEMA ##
{{{{ 
  "tech_stack": {{
    "frontend": ["React", "Next.js", "Tailwind CSS"],
    "backend": ["Python", "FastAPI", "RESTful APIs"],
    "database": ["PostgreSQL", "Redis", "Pinecone"],
    "ai_ml": ["OpenAI API", "LangChain", "PyTorch"],
    "deployment": ["AWS Lambda", "Docker", "CloudFront"],
    "testing_devops": ["Jest", "Playwright", "GitHub Actions"]
  }},
  "follow_up_question": "A question connecting stack suggestions to overall scope."
}}}}
"""
)

work_scope_prompt = PromptTemplate(
    input_variables=["parsed_data", "user_feedback", "approved_summary", "approved_features", "approved_tech_stack"],
    template="""
You are a professional Project Planner and Work Scope Generator. Your task is to generate a comprehensive project work scope document based on all approved project components and the initial information provided.

<context>
{parsed_data}
</context>

<approved_summary>
{approved_summary}
</approved_summary>

<approved_features>
{approved_features}
</approved_features>

<approved_tech_stack>
{approved_tech_stack}
</approved_tech_stack>

<user_feedback>
{user_feedback}
</user_feedback>

## Core Task:
Generate a comprehensive project work scope document. If user feedback is provided, refine the work scope accordingly.

## Internal Reasoning (Before Generating - Do Not Output):
1.  **Review All Inputs:** Holistically review the summary, features, tech stack, and original context.
2.  **Incorporate Feedback:** How does the user's latest feedback impact the overall plan? Does it change a milestone, a feature's scope, or a client responsibility?
3.  **Structure the Document:** Mentally outline the entire work scope. How do the features translate into a feature breakdown and milestone plan? How does the tech stack inform deliverables and technical requirements?
4.  **Identify Uncertainties:** Are there any gaps in the provided information that will prevent me from completing a section (e.g., cannot create a realistic milestone plan without more detail)? Note these for the Uncertainty Protocol.
5.  **Draft Content:** Systematically generate each section of the document based on this internal plan.

## Operational Guidelines:
-   Carefully integrate the approved summary, features, and tech stack into the work scope.
-   Be accurate and realistic in estimations and descriptions.
-   **Uncertainty Protocol:** If any section of the work scope cannot be completed due to missing information (e.g., lack of detail for a milestone plan), clearly state 'Information Required' for that section and specify what details are needed to complete it.
-   Use a professional, client-ready tone with consistent structure.

## Output Structure:

Overview:
-   Summarize the overall purpose of the system based on the approved summary.
-   Identify the business goals, target regions, and intended users from the context and summary.
-   Mention key architectural or compliance considerations from the tech stack.
-   Return a single paragraph.

User Roles and Key Features:
-   Define user roles (e.g., Admin, Client, End-User) based on context and features.
-   List key features and responsibilities for each role, incorporating approved features.

Feature Breakdown:
-   Categorize and detail all approved features, grouped by functional area or module. For each feature, describe its core functionality, scope, and key tasks.

Workflow:
-   Describe the end-to-end system interaction flow in clear, sequential steps based on approved features.

Milestone Plan:
-   Break development into logical milestones based on features and tech stack, including title, estimated duration, and key deliverables.

Tech Stack:
-   List the approved technologies concisely under their respective headings. Do not add new descriptions.

Deliverables:
-   List tangible outputs (e.g., deployed apps, APIs, documentation) for each milestone.

Out of Scope:
-   Clearly list items not included, such as ongoing maintenance, third-party service costs, etc.

Client Responsibilities:
-   List items required from the client (e.g., hosting credentials, API keys, timely feedback).

Technical Requirements:
-   List non-functional requirements from context and tech stack (e.g., performance, security, compliance).

General Notes:
-   Include notes on payment, communication, QA, and post-launch support.

Effort Estimation Hours:
-   Generate a table with columns: Module, Min Hours, Max Hours.
-   Modules should include: Frontend, Backend, Database, AI/ML (if applicable), DevOps, and Project Management.
-   Include a Total row.

## Output Requirements:
- Your entire response MUST be a single, valid JSON object that strictly adheres to the schema below.
- Do not include any introductory text, explanations, closing remarks, or markdown formatting like ```json before or after the JSON object.

## JSON SCHEMA ##
{{{{ 
  "overview": "Summary of the project's purpose, goals, and key considerations.",
  "user_roles_and_key_features": "List of user roles and their core responsibilities, formatted as a string with \\n for newlines.",
  "feature_breakdown": "Grouped feature list with descriptions, formatted as a string with \\n for newlines.",
  "workflow": "Step-by-step interaction flow, formatted as a string with \\n for newlines.",
  "milestone_plan": "List of milestones with duration and deliverables, formatted as a string with \\n for newlines.",
  "tech_stack": {{
    "frontend": ["React", "Next.js"],
    "backend": ["Python", "FastAPI"],
    "database": ["PostgreSQL", "Redis"],
    "ai_ml": ["OpenAI API", "LangChain"],
    "deployment": ["AWS", "Docker"],
    "testing_devops": ["Pytest", "Jest"]
  }},
  "deliverables": "Project deliverables, formatted as a string with \\n for newlines.",
  "out_of_scope": "Excluded work and responsibilities, formatted as a string with \\n for newlines.",
  "client_responsibilities": "Items or actions required from the client, formatted as a string with \\n for newlines.",
  "technical_requirements": "Non-functional and compliance requirements, formatted as a string with \\n for newlines.",
  "general_notes": "Notes on QA, support, payment, and communication, formatted as a string with \\n for newlines.",
  "effort_estimation_table": {{
    "headers": ["Module", "Min Hours", "Max Hours"],
    "rows": [
      ["Frontend", "40", "60"],
      ["Backend", "50", "70"],
      ["Database", "20", "30"],
      ["AI/ML", "60", "80"],
      ["DevOps", "25", "35"],
      ["Project Management", "30", "40"],
      ["Total", "225", "315"]
    ]
  }},
  "follow_up_question": "One natural-language question to validate or clarify scope or assumptions."
}}}}
"""
)


router_prompt = PromptTemplate(
    input_variables=["user_input", "current_stage", "current_content"],
    template="""
You are a Router Agent. Analyze the user input and determine the appropriate action.

Current Stage: {current_stage}
Current Content: {current_content}
User Input: {user_input}

You must choose one of the following actions:
ACTION: [APPROVE or EDIT]
FEEDBACK: [If the action is EDIT, provide the original user's input directly. If the action is APPROVE, leave this empty.]

Examples:
User Input: "yes, this works"
ACTION: APPROVE
FEEDBACK: 

User Input: "reword the introduction"
ACTION: EDIT
FEEDBACK: reword the introduction

User Input: "can you make the tone more formal?"
ACTION: EDIT
FEEDBACK: can you make the tone more formal?

User Input: "That's great, let's proceed."
ACTION: APPROVE
FEEDBACK: 
"""
)
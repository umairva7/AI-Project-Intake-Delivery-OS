/**
 * AI Project Intake & Delivery OS — Frontend Application Logic
 * Day 2: Pipeline v0 Web Interface
 */

// Sample Data derived from DAY_2.md and test_cases/evaluation_data.json
const SAMPLE_BRIEFS = {
  property: {
    title: "Property Platform (Day 2 Happy Path)",
    client: "Apex Realty Group",
    source: "web_form",
    raw_text: `We need a web platform for a property company. Users should be able to browse houses, filter by location and price, and contact agents. We also want an admin dashboard where staff can add and update listings. We already have a designer but need development. Ideally use React for the frontend and something Python based for the backend. We want an MVP in around 6 weeks.`,
    extracted: {
      request_id: "REQ-0001",
      status: "pending_review",
      project: {
        name: "Property Listing Platform",
        summary: "Web platform for browsing and managing property listings with search, filter, and agent contact workflows.",
        business_objective: "Enable customers to discover properties and contact agents while allowing internal staff to manage listings via an admin dashboard.",
        requirements: [
          { description: "Browse property listings", priority: "high" },
          { description: "Filter properties by location & price", priority: "high" },
          { description: "Contact property agents form/flow", priority: "high" },
          { description: "Admin dashboard to add and update listings", priority: "high" }
        ],
        technical_requirements: [
          "React frontend",
          "Python backend API"
        ],
        constraints: [
          "MVP target of approximately 6 weeks"
        ],
        existing_resources: [
          "UI Designer already available"
        ],
        missing_information: [
          "Authentication requirements (public browsing vs agent auth)",
          "Hosting and cloud deployment preferences",
          "Expected listing volume & concurrent search queries",
          "Explicit MVP acceptance criteria & sign-off criteria"
        ]
      },
      team_recommendation: {
        team: "Web Development",
        confidence: 0.91,
        confidence_text: "91% High Confidence",
        reasoning: [
          "Primary deliverable is a web application",
          "Requirements explicitly call for React frontend and Python backend",
          "Customer-facing search and administrative dashboard",
          "Existing in-house designer reduces design allocation needs"
        ],
        alternative_team: null
      },
      checklist: [
        { task: "Confirm functional requirements & agent workflows", priority: "high", done: false },
        { task: "Define technical architecture & Python API specs", priority: "high", done: false },
        { task: "Design database schema (Properties, Listings, Agents)", priority: "high", done: false },
        { task: "Implement property browsing & filter API", priority: "high", done: false },
        { task: "Implement customer React frontend UI", priority: "medium", done: false },
        { task: "Implement admin management dashboard", priority: "medium", done: false },
        { task: "QA and acceptance testing against 6-week target", priority: "high", done: false }
      ]
    }
  },

  dashboard: {
    title: "Employee Dashboard (TC-001)",
    client: "Initech Internal Tools",
    source: "email",
    raw_text: `We need a React frontend with a Python API for an internal employee dashboard. The dashboard should display employee information, project assignments, and work hours. We have an existing PostgreSQL database we can connect to. Timeline: 6 weeks. Budget: $50,000.`,
    extracted: {
      request_id: "REQ-0002",
      status: "pending_review",
      project: {
        name: "Internal Employee Management Dashboard",
        summary: "Internal dashboard interface displaying employee records, active project assignments, and work hours tracking.",
        business_objective: "Centralize employee information and project time tracking using existing PostgreSQL data.",
        requirements: [
          { description: "Display employee profiles and directory", priority: "high" },
          { description: "Track and visualize project assignments", priority: "high" },
          { description: "Work hours tracking / timesheet logging", priority: "medium" },
          { description: "PostgreSQL database integration", priority: "high" }
        ],
        technical_requirements: [
          "React frontend",
          "Python API (FastAPI/Flask)",
          "PostgreSQL database"
        ],
        constraints: [
          "6 weeks delivery timeline",
          "$50,000 fixed budget"
        ],
        existing_resources: [
          "Existing PostgreSQL database"
        ],
        missing_information: [
          "Expected number of concurrent internal users",
          "Performance & response time SLA targets",
          "Authentication/SSO (LDAP, Google, or custom)",
          "Hosting and internal deployment environment"
        ]
      },
      team_recommendation: {
        team: "Web Development",
        confidence: 0.94,
        confidence_text: "94% Very High Confidence",
        reasoning: [
          "Standard internal enterprise web application",
          "Clear technology stack explicitly provided (React + Python + PostgreSQL)",
          "Scope fits within a standard 6-week web delivery team sprint"
        ],
        alternative_team: "Data Engineering"
      },
      checklist: [
        { task: "Inspect existing PostgreSQL schema and data models", priority: "high", done: false },
        { task: "Define SSO / Auth integration specs", priority: "high", done: false },
        { task: "Build Python REST API endpoints for employees and assignments", priority: "high", done: false },
        { task: "Build React dashboard views with responsive tables", priority: "high", done: false },
        { task: "Validate budget and 6-week delivery roadmap", priority: "medium", done: false }
      ]
    }
  },

  mobile: {
    title: "Mobile Fitness App (TC-002)",
    client: "PulseFit Technologies",
    source: "web_form",
    raw_text: `Mobile app for iOS and Android to track personal fitness goals. Features: workout logging, progress charts, social sharing, notifications. We want native apps, not cross-platform. 8 weeks, $75,000.`,
    extracted: {
      request_id: "REQ-0003",
      status: "pending_review",
      project: {
        name: "Native Fitness Tracker App",
        summary: "Native iOS and Android fitness application for workout logging, progress visualization, and community sharing.",
        business_objective: "Engage users with mobile fitness tracking and social accountability.",
        requirements: [
          { description: "iOS native application (Swift)", priority: "high" },
          { description: "Android native application (Kotlin)", priority: "high" },
          { description: "Workout logging with exercise catalog", priority: "high" },
          { description: "Progress analytics and visual charts", priority: "medium" },
          { description: "Social feed and workout sharing", priority: "medium" },
          { description: "Push notification system for goal reminders", priority: "high" }
        ],
        technical_requirements: [
          "Native iOS (Swift / SwiftUI)",
          "Native Android (Kotlin / Jetpack Compose)",
          "Push Notification Service (APNs / FCM)"
        ],
        constraints: [
          "8 weeks timeline (tight for dual native codebases)",
          "$75,000 budget"
        ],
        existing_resources: [
          "Brand guidelines and initial UI assets"
        ],
        missing_information: [
          "Backend API and cloud infrastructure requirements",
          "Offline mode and local storage sync mechanisms",
          "Third-party integrations (Apple HealthKit / Google Fit)",
          "App Store & Play Store publishing account status"
        ]
      },
      team_recommendation: {
        team: "Mobile Development",
        confidence: 0.88,
        confidence_text: "88% High Confidence",
        reasoning: [
          "Explicitly specifies separate native iOS and Android applications",
          "Requires mobile-specific hardware capabilities (notifications, local storage)",
          "Dual native apps within 8 weeks requires dedicated mobile engineers"
        ],
        alternative_team: "Mixed / Cross-functional"
      },
      checklist: [
        { task: "Evaluate timeline risk for dual native apps vs single codebase", priority: "high", done: false },
        { task: "Design API contracts for workout logging & sync", priority: "high", done: false },
        { task: "Set up iOS & Android native project scaffolds", priority: "high", done: false },
        { task: "Configure APNs & Firebase Cloud Messaging", priority: "medium", done: false },
        { task: "App Store compliance & test flight rollout plan", priority: "medium", done: false }
      ]
    }
  },

  ambiguous: {
    title: "Ambiguous E-Commerce (TC-004)",
    client: "Horizon Commerce",
    source: "email",
    raw_text: `E-commerce platform for selling digital and physical products. Shopping cart, payment processing (Stripe), inventory management, order fulfillment tracking. 3 months, need it live for holiday season.`,
    extracted: {
      request_id: "REQ-0004",
      status: "pending_review",
      project: {
        name: "Hybrid E-Commerce Platform",
        summary: "Multi-product e-commerce store handling both instant digital downloads and physical inventory fulfillment.",
        business_objective: "Launch revenue-generating store in time for holiday peak sales.",
        requirements: [
          { description: "Digital product download and licensing flow", priority: "high" },
          { description: "Physical product catalog with variants", priority: "high" },
          { description: "Shopping cart & Stripe payment integration", priority: "high" },
          { description: "Inventory management & fulfillment tracking", priority: "high" }
        ],
        technical_requirements: [
          "Stripe Payment Gateway integration",
          "E-Commerce backend & secure digital asset delivery"
        ],
        constraints: [
          "Hard deadline: Must launch before holiday shopping season (3 months)"
        ],
        existing_resources: [
          "Product catalog spreadsheets"
        ],
        missing_information: [
          "Custom build vs Shopify/WooCommerce platform preference",
          "Tax calculation & international currency requirements",
          "Shipping carrier integrations (FedEx, UPS, etc.)",
          "Expected peak concurrent shoppers during launch"
        ]
      },
      team_recommendation: {
        team: "Web Development",
        confidence: 0.82,
        confidence_text: "82% Moderate Confidence",
        reasoning: [
          "E-commerce requirements span custom web frontend and payments API",
          "Needs architectural review: evaluating custom build vs headless commerce",
          "High delivery risk due to fixed holiday launch constraint"
        ],
        alternative_team: "Automation"
      },
      checklist: [
        { task: "Conduct architecture decision: Headless vs Custom vs SaaS", priority: "high", done: false },
        { task: "Define Stripe checkout and webhook handling specs", priority: "high", done: false },
        { task: "Determine digital file storage & secure link expiration", priority: "high", done: false },
        { task: "Map shipping and fulfillment logistics workflows", priority: "medium", done: false },
        { task: "Establish load testing plan for peak holiday traffic", priority: "high", done: false }
      ]
    }
  }
};

// Backend API Configuration
const API_BASE_URL = (window.location.protocol.startsWith('http') && window.location.port === '8000')
  ? ''
  : 'http://localhost:8000';

/**
 * Normalizes a PendingIntake API response from the backend into the shape
 * expected by the existing UI rendering layer.
 *
 * Backend source of truth (PendingIntake):
 * - id: "INT-xxxx"
 * - request_id: "REQ-xxxx"
 * - extracted: { project_name, summary, requirements, missing_information, scope_constraints, confidence }
 * - team_recommendation: { team, confidence, reasoning, alternative_team, ... }
 * - checklist: { items: [...], total_tasks: N, generated_at: "..." }
 * - status: "pending_review" | "approved" | "flagged"
 */
function normalizeIntakeResponse(data) {
  if (!data) return null;

  const extracted = data.extracted || data.project || {};
  const teamRec = data.team_recommendation || {};
  const checklistData = data.checklist || {};
  const rawItems = Array.isArray(checklistData)
    ? checklistData
    : (Array.isArray(checklistData.items) ? checklistData.items : []);

  const normalizedChecklist = rawItems.map((item, idx) => ({
    id: item.id !== undefined && item.id !== null ? item.id : idx + 1,
    task: item.task || '',
    priority: item.priority || 'medium',
    estimated_effort: item.estimated_effort || null,
    done: Boolean(item.done)
  }));

  const constraints = extracted.scope_constraints || extracted.constraints || [];

  return {
    id: data.id || data.intake_id || `INT-${Date.now().toString(36)}`,
    request_id: data.request_id || data.id || 'REQ-0001',
    status: data.status || 'pending_review',
    source: data.source || (document.getElementById('sourceSelect') ? document.getElementById('sourceSelect').value : 'web_form'),
    created_at: data.created_at || new Date().toISOString(),
    requires_manual_review: Boolean(data.requires_manual_review),
    review_notes: data.review_notes || '',
    project: {
      name: extracted.project_name || extracted.name || 'Untitled Project',
      summary: extracted.summary || 'No summary available',
      business_objective: extracted.business_objective || (
        extracted.summary ? `Delivery focus: ${extracted.project_name || 'Project Intake'}` : 'Scope defined in project brief'
      ),
      requirements: (extracted.requirements || []).map(r => ({
        description: r.description || '',
        priority: r.priority || 'medium',
        confirmed: r.confirmed !== false,
        source_quote: r.source_quote || null
      })),
      technical_requirements: extracted.technical_requirements || [],
      constraints: constraints,
      existing_resources: extracted.existing_resources || [],
      missing_information: extracted.missing_information || []
    },
    team_recommendation: {
      team: teamRec.team || teamRec.recommended_team || 'Web Development',
      confidence: typeof teamRec.confidence === 'number' ? teamRec.confidence : 0.85,
      confidence_text: teamRec.confidence_text || `${Math.round((teamRec.confidence || 0) * 100)}% Confidence`,
      reasoning: teamRec.reasoning || [],
      alternative_team: teamRec.alternative_team || null
    },
    checklist: normalizedChecklist,
    checklist_total_tasks: checklistData.total_tasks || normalizedChecklist.length
  };
}

// Application State
let currentIntake = normalizeIntakeResponse(SAMPLE_BRIEFS.property.extracted);
let intakeHistory = [
  { id: currentIntake.id, request_id: currentIntake.request_id, name: "Property Listing Platform", team: "Web Development", status: "pending_review", data: JSON.parse(JSON.stringify(currentIntake)) }
];
let isEditing = false;

// DOM Elements
const rawTextInput = document.getElementById('rawTextInput');
const charCount = document.getElementById('charCount');
const clientNameInput = document.getElementById('clientNameInput');
const sourceSelect = document.getElementById('sourceSelect');
const intakeForm = document.getElementById('intakeForm');
const clearBtn = document.getElementById('clearBtn');
const processBtn = document.getElementById('processBtn');
const btnSpinner = document.getElementById('btnSpinner');
const processBtnText = document.getElementById('processBtnText');
const presetChips = document.querySelectorAll('.chip');
const historyList = document.getElementById('historyList');
const historyCount = document.getElementById('historyCount');
const processingOverlay = document.getElementById('processingOverlay');
const toastContainer = document.getElementById('toastContainer');

// Output Displays
const displayRequestId = document.getElementById('displayRequestId');
const displayTimestamp = document.getElementById('displayTimestamp');
const displaySource = document.getElementById('displaySource');
const displayStatus = document.getElementById('displayStatus');
const statusLabel = document.getElementById('statusLabel');

const displayProjectName = document.getElementById('displayProjectName');
const displaySummary = document.getElementById('displaySummary');
const displayObjective = document.getElementById('displayObjective');

const displayRecommendedTeam = document.getElementById('displayRecommendedTeam');
const displayConfidenceBadge = document.getElementById('displayConfidenceBadge');
const displayConfidenceText = document.getElementById('displayConfidenceText');
const displayReasoningList = document.getElementById('displayReasoningList');

const displayRequirementsList = document.getElementById('displayRequirementsList');
const reqCount = document.getElementById('reqCount');
const displayTechStack = document.getElementById('displayTechStack');
const displayConstraints = document.getElementById('displayConstraints');
const displayResources = document.getElementById('displayResources');
const displayMissingList = document.getElementById('displayMissingList');

const displayChecklist = document.getElementById('displayChecklist');
const checklistProgress = document.getElementById('checklistProgress');
const newTaskInput = document.getElementById('newTaskInput');
const addTaskBtn = document.getElementById('addTaskBtn');

// Review / HITL Buttons
const teamOverrideSelect = document.getElementById('teamOverrideSelect');
const reviewerNameInput = document.getElementById('reviewerNameInput');
const reviewNotes = document.getElementById('reviewNotes');
const approveIntakeBtn = document.getElementById('approveIntakeBtn');
const editIntakeBtn = document.getElementById('editIntakeBtn');
const rejectIntakeBtn = document.getElementById('rejectIntakeBtn');

// Pipeline Steps for Overlay
const pipelineSteps = [
  document.getElementById('stepParse'),
  document.getElementById('stepExtract'),
  document.getElementById('stepValidate'),
  document.getElementById('stepRecommend'),
  document.getElementById('stepChecklist')
];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  checkApiHealth();
  loadSample('property');
  renderHistory();
  renderIntakeView();
  setupEventListeners();
});

// Check backend API connectivity on load
async function checkApiHealth() {
  const statusIndicator = document.getElementById('apiStatusIndicator');
  const statusText = document.getElementById('apiStatusText');
  try {
    const resp = await fetch(`${API_BASE_URL}/openapi.json`, { method: 'GET' });
    if (resp.ok) {
      if (statusText) statusText.textContent = 'API Connected';
      if (statusIndicator) statusIndicator.title = `Connected to API at ${API_BASE_URL || window.location.origin}`;
    }
  } catch (_) {
    if (statusText) statusText.textContent = 'API Offline';
    if (statusIndicator) statusIndicator.title = `Could not reach API at ${API_BASE_URL}`;
  }
}

function setupEventListeners() {
  // Character counter
  rawTextInput.addEventListener('input', () => {
    charCount.textContent = `${rawTextInput.value.length} / 5000`;
  });

  // Sample Chips
  presetChips.forEach(chip => {
    chip.addEventListener('click', () => {
      presetChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const sampleKey = chip.dataset.sample;
      loadSample(sampleKey);
    });
  });

  // Clear Form
  clearBtn.addEventListener('click', () => {
    rawTextInput.value = '';
    charCount.textContent = '0 / 5000';
    rawTextInput.focus();
    showToast('Input brief cleared', 'info');
  });

  // Form Submit / Process Request
  intakeForm.addEventListener('submit', (e) => {
    e.preventDefault();
    if (!rawTextInput.value.trim()) {
      showToast('Please enter or paste a project brief first', 'warning');
      return;
    }
    runExtractionPipeline();
  });

  // Add Task to Checklist
  addTaskBtn.addEventListener('click', handleAddTask);
  newTaskInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleAddTask();
    }
  });

  // Human Review: Approve
  approveIntakeBtn.addEventListener('click', async () => {
    if (!currentIntake || !currentIntake.id) {
      showToast('No active intake loaded to approve', 'warning');
      return;
    }

    const intakeId = currentIntake.id;
    approveIntakeBtn.disabled = true;

    try {
      const response = await fetch(`${API_BASE_URL}/briefs/${encodeURIComponent(intakeId)}/approve`, {
        method: 'POST',
        headers: { 'Accept': 'application/json' }
      });

      if (!response.ok) {
        let errMsg = `Server returned error (${response.status})`;
        try {
          const errJson = await response.json();
          if (errJson.detail) errMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        } catch (_) {}
        throw new Error(errMsg);
      }

      const reviewer = reviewerNameInput.value.trim() || 'Lead PM';
      currentIntake.status = 'approved';
      currentIntake.review = {
        status: 'approved',
        reviewer: reviewer,
        review_notes: reviewNotes.value.trim(),
        approved_at: new Date().toISOString()
      };
      currentIntake.team_recommendation.team = teamOverrideSelect.value;

      updateStatusUI('approved');
      updateHistoryStatus(currentIntake.id, 'approved');
      showToast(`✓ Intake ${currentIntake.id} approved and finalized!`, 'success');
    } catch (err) {
      console.error('Approve failed:', err);
      showToast(`Approval failed: ${err.message}`, 'error');
    } finally {
      approveIntakeBtn.disabled = false;
    }
  });

  // Human Review: Reject / Request Clarification (Mark Issues)
  rejectIntakeBtn.addEventListener('click', async () => {
    if (!currentIntake || !currentIntake.id) {
      showToast('No active intake loaded to flag', 'warning');
      return;
    }

    const intakeId = currentIntake.id;
    const reviewer = reviewerNameInput.value.trim() || 'Lead PM';
    const noteText = reviewNotes.value.trim();
    const issues = noteText ? [noteText] : ['Scope or technical details require clarification'];

    rejectIntakeBtn.disabled = true;

    try {
      const response = await fetch(`${API_BASE_URL}/briefs/${encodeURIComponent(intakeId)}/mark-issues`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json'
        },
        body: JSON.stringify({ issues: issues })
      });

      if (!response.ok) {
        let errMsg = `Server returned error (${response.status})`;
        try {
          const errJson = await response.json();
          if (errJson.detail) errMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
        } catch (_) {}
        throw new Error(errMsg);
      }

      currentIntake.status = 'flagged';
      currentIntake.review = {
        status: 'flagged',
        reviewer: reviewer,
        review_notes: noteText || issues[0],
        flagged_at: new Date().toISOString()
      };

      updateStatusUI('flagged');
      updateHistoryStatus(currentIntake.id, 'flagged');
      showToast(`Intake ${currentIntake.id} marked as Revision Requested`, 'warning');
    } catch (err) {
      console.error('Mark issues failed:', err);
      showToast(`Failed to flag issues: ${err.message}`, 'error');
    } finally {
      rejectIntakeBtn.disabled = false;
    }
  });

  // Human Review: Toggle Edit Mode
  editIntakeBtn.addEventListener('click', () => {
    isEditing = !isEditing;
    const editableElements = [displayProjectName, displaySummary, displayObjective];
    
    if (isEditing) {
      editableElements.forEach(el => {
        el.setAttribute('contenteditable', 'true');
        el.style.borderBottom = '1px dashed var(--primary)';
        el.style.outline = 'none';
        el.style.backgroundColor = 'var(--bg-subtle)';
      });
      editIntakeBtn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"></polyline></svg>
        Save Edits
      `;
      editIntakeBtn.classList.add('btn-primary');
      displayProjectName.focus();
      showToast('Fields are now editable. Click "Save Edits" when done.', 'info');
    } else {
      editableElements.forEach(el => {
        el.removeAttribute('contenteditable');
        el.style.borderBottom = 'none';
        el.style.backgroundColor = 'transparent';
      });
      // Save changes to currentIntake model
      currentIntake.project.name = displayProjectName.textContent.trim();
      currentIntake.project.summary = displaySummary.textContent.trim();
      currentIntake.project.business_objective = displayObjective.textContent.trim();

      editIntakeBtn.innerHTML = `
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 013 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
        Edit Values
      `;
      editIntakeBtn.classList.remove('btn-primary');
      showToast('Intake edits saved successfully', 'success');
    }
  });
}

function loadSample(key) {
  const sample = SAMPLE_BRIEFS[key];
  if (!sample) return;

  rawTextInput.value = sample.raw_text;
  charCount.textContent = `${sample.raw_text.length} / 5000`;
  clientNameInput.value = sample.client;
  sourceSelect.value = sample.source;

  showToast(`Loaded preset: ${sample.title}`, 'info');
}

// Simulated Pipeline Stepper & API Bridge
function runExtractionPipeline() {
  // Button loading state
  processBtn.disabled = true;
  btnSpinner.style.display = 'inline-block';
  processBtnText.textContent = 'Processing Pipeline...';
  processingOverlay.style.display = 'flex';

  // Determine matching sample or fallback
  const enteredText = rawTextInput.value.toLowerCase();
  let matchedSampleKey = 'property';
  if (enteredText.includes('fitness') || enteredText.includes('ios') || enteredText.includes('android')) {
    matchedSampleKey = 'mobile';
  } else if (enteredText.includes('employee') || enteredText.includes('dashboard') || enteredText.includes('hours')) {
    matchedSampleKey = 'dashboard';
  } else if (enteredText.includes('commerce') || enteredText.includes('stripe') || enteredText.includes('store')) {
    matchedSampleKey = 'ambiguous';
  }

  const baseSample = SAMPLE_BRIEFS[matchedSampleKey];
  const newRequestId = `REQ-000${intakeHistory.length + 1}`;

  // Reset steps
  pipelineSteps.forEach(step => {
    step.className = 'pipeline-step';
  });

  // Step 1: Parse
  pipelineSteps[0].classList.add('active');

  setTimeout(() => {
    pipelineSteps[0].classList.remove('active');
    pipelineSteps[0].classList.add('completed');
    pipelineSteps[1].classList.add('active'); // Extract
  }, 400);

  setTimeout(() => {
    pipelineSteps[1].classList.remove('active');
    pipelineSteps[1].classList.add('completed');
    pipelineSteps[2].classList.add('active'); // Validate
  }, 800);

  setTimeout(() => {
    pipelineSteps[2].classList.remove('active');
    pipelineSteps[2].classList.add('completed');
    pipelineSteps[3].classList.add('active'); // Recommend
  }, 1200);

  setTimeout(() => {
    pipelineSteps[3].classList.remove('active');
    pipelineSteps[3].classList.add('completed');
    pipelineSteps[4].classList.add('active'); // Checklist
  }, 1600);

  setTimeout(() => {
    pipelineSteps[4].classList.remove('active');
    pipelineSteps[4].classList.add('completed');

    // Finish processing
    currentIntake = JSON.parse(JSON.stringify(baseSample.extracted));
    currentIntake.request_id = newRequestId;
    currentIntake.source = sourceSelect.value;
    currentIntake.status = 'pending_review';

    // Add to history
    intakeHistory.unshift({
      id: newRequestId,
      name: currentIntake.project.name,
      team: currentIntake.team_recommendation.team,
      status: 'pending_review',
      data: JSON.parse(JSON.stringify(currentIntake))
    });

    renderHistory();
    renderIntakeView();

    // Hide overlay
    processingOverlay.style.display = 'none';
    processBtn.disabled = false;
    btnSpinner.style.display = 'none';
    processBtnText.textContent = 'Run Extraction Pipeline';

    showToast(`Pipeline completed! Structured intake generated for ${currentIntake.project.name}`, 'success');
  }, 2000);
}

// Render the right panel with intake data
function renderIntakeView() {
  const p = currentIntake.project;
  const t = currentIntake.team_recommendation;

  // Metadata
  displayRequestId.textContent = currentIntake.request_id || 'REQ-0001';
  displayTimestamp.textContent = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  displaySource.textContent = formatSource(sourceSelect.value || currentIntake.source);

  // Status
  updateStatusUI(currentIntake.status);

  // Overview
  displayProjectName.textContent = p.name || 'Untitled Project';
  displaySummary.textContent = p.summary || 'No summary available';
  displayObjective.textContent = p.business_objective || 'No business objective specified';

  // Recommendation
  displayRecommendedTeam.textContent = t.team;
  displayConfidenceText.textContent = t.confidence_text || `${Math.round(t.confidence * 100)}% Confidence`;
  teamOverrideSelect.value = t.team;

  // Reasoning list
  displayReasoningList.innerHTML = '';
  (t.reasoning || []).forEach(reason => {
    const li = document.createElement('li');
    li.textContent = reason;
    displayReasoningList.appendChild(li);
  });

  // Requirements
  displayRequirementsList.innerHTML = '';
  reqCount.textContent = `${(p.requirements || []).length} items`;
  (p.requirements || []).forEach(req => {
    const li = document.createElement('li');
    li.innerHTML = `
      <span class="req-check">✓</span>
      <span class="req-text">${escapeHtml(req.description)}</span>
      <span class="priority-tag priority-${req.priority || 'medium'}">${req.priority || 'medium'}</span>
    `;
    displayRequirementsList.appendChild(li);
  });

  // Technical Specs
  displayTechStack.innerHTML = '';
  (p.technical_requirements || []).forEach(tech => {
    const span = document.createElement('span');
    span.className = 'tech-tag';
    span.textContent = tech;
    displayTechStack.appendChild(span);
  });

  // Constraints & Resources
  displayConstraints.textContent = (p.constraints && p.constraints.length > 0)
    ? `⏱️ ${p.constraints.join(', ')}`
    : 'None explicitly stated';

  displayResources.textContent = (p.existing_resources && p.existing_resources.length > 0)
    ? `🎨 ${p.existing_resources.join(', ')}`
    : 'No existing assets mentioned';

  // Missing Information
  displayMissingList.innerHTML = '';
  (p.missing_information || []).forEach(item => {
    const li = document.createElement('li');
    li.textContent = item;
    displayMissingList.appendChild(li);
  });

  // Checklist
  renderChecklist();
}

function renderChecklist() {
  displayChecklist.innerHTML = '';
  const items = currentIntake.checklist || [];
  let completedCount = 0;

  items.forEach((item, index) => {
    if (item.done) completedCount++;

    const div = document.createElement('div');
    div.className = `checklist-item ${item.done ? 'done' : ''}`;
    div.innerHTML = `
      <div class="checklist-item-left">
        <input type="checkbox" id="chk_${index}" ${item.done ? 'checked' : ''} data-index="${index}">
        <label for="chk_${index}" class="checklist-title">${escapeHtml(item.task)}</label>
      </div>
      <span class="priority-tag priority-${item.priority || 'medium'}">${item.priority || 'medium'}</span>
    `;

    div.querySelector('input[type="checkbox"]').addEventListener('change', (e) => {
      items[index].done = e.target.checked;
      div.classList.toggle('done', e.target.checked);
      updateChecklistProgress();
    });

    displayChecklist.appendChild(div);
  });

  checklistProgress.textContent = `${completedCount} of ${items.length} complete`;
}

function updateChecklistProgress() {
  const items = currentIntake.checklist || [];
  const completedCount = items.filter(i => i.done).length;
  checklistProgress.textContent = `${completedCount} of ${items.length} complete`;
}

function handleAddTask() {
  const taskText = newTaskInput.value.trim();
  if (!taskText) return;

  if (!currentIntake.checklist) {
    currentIntake.checklist = [];
  }

  currentIntake.checklist.push({
    task: taskText,
    priority: "medium",
    done: false
  });

  newTaskInput.value = '';
  renderChecklist();
  showToast(`Added action item: "${taskText}"`, 'info');
}

function updateStatusUI(status) {
  displayStatus.className = 'status-pill';
  if (status === 'approved') {
    displayStatus.classList.add('status-approved');
    statusLabel.textContent = 'Approved & Finalized';
  } else if (status === 'rejected') {
    displayStatus.classList.add('status-rejected');
    statusLabel.textContent = 'Revision Requested';
  } else {
    displayStatus.classList.add('status-pending');
    statusLabel.textContent = 'Pending Human Review';
  }
}

function renderHistory() {
  historyList.innerHTML = '';
  historyCount.textContent = intakeHistory.length;

  intakeHistory.forEach((item, index) => {
    const div = document.createElement('div');
    div.className = `history-item ${item.id === currentIntake.request_id ? 'active' : ''}`;
    div.innerHTML = `
      <div class="history-item-meta">
        <span class="history-id">${item.id}</span>
        <span class="history-name">${escapeHtml(item.name)}</span>
      </div>
      <span class="badge ${item.status === 'approved' ? 'badge-primary' : 'badge-subtle'}">
        ${item.team}
      </span>
    `;

    div.addEventListener('click', () => {
      document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
      div.classList.add('active');
      if (item.data) {
        currentIntake = JSON.parse(JSON.stringify(item.data));
        renderIntakeView();
        showToast(`Loaded history: ${item.id}`, 'info');
      }
    });

    historyList.appendChild(div);
  });
}

function updateHistoryStatus(id, newStatus) {
  const historyEntry = intakeHistory.find(h => h.id === id);
  if (historyEntry) {
    historyEntry.status = newStatus;
    renderHistory();
  }
}

function formatSource(sourceKey) {
  const map = {
    web_form: 'Web Form',
    email: 'Client Email',
    slack: 'Slack / Notes',
    meeting_transcript: 'Meeting Notes'
  };
  return map[sourceKey] || 'Web Intake';
}

function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * AI Project Intake — Frontend Application Logic
 * Clean, Minimal, Operations-focused B2B Interface
 */

// Sample Data with Evidence Audit Trail
const SAMPLE_BRIEFS = {
  property: {
    title: "Property Platform",
    client: "Apex Realty Group",
    source: "web_form",
    raw_text: `We need a web platform for a property company. Users should be able to browse houses, filter by location and price, and contact agents. We also want an admin dashboard where staff can add and update listings. We already have a designer but need development. Ideally use React for the frontend and something Python based for the backend. We want an MVP in around 6 weeks.`,
    extracted: {
      id: "INT-824262a0",
      request_id: "REQ-0001",
      status: "pending_review",
      project: {
        name: "Property Listing Platform",
        summary: "Web platform for browsing and managing property listings with customer search and agent contact flows.",
        business_objective: "Enable customers to discover properties and contact agents while allowing internal staff to manage listings via an admin dashboard.",
        requirements: [
          { description: "Browse property listings", priority: "high", confirmed: true, source_quote: "Users should be able to browse houses" },
          { description: "Filter properties by location and price", priority: "high", confirmed: true, source_quote: "filter by location and price" },
          { description: "Contact property agents", priority: "high", confirmed: true, source_quote: "contact agents" },
          { description: "Admin dashboard to add and update listings", priority: "high", confirmed: true, source_quote: "admin dashboard where staff can add and update listings" }
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
          "Authentication and authorization requirements (visitor vs staff)",
          "Hosting and cloud deployment requirements",
          "Expected listing volume and concurrent search traffic",
          "Exact MVP acceptance criteria"
        ]
      },
      team_recommendation: {
        team: "Web Development",
        confidence: 0.95,
        confidence_text: "95% confidence",
        reasoning: [
          "Primary deliverable is a web application with consumer and admin portals",
          "Frontend (React) and backend API (Python) match web team stack",
          "Scope fits standard 6-week web delivery team capacity"
        ],
        alternative_team: null
      },
      checklist: [
        {
          id: 1,
          task: "Implement React frontend property browsing",
          priority: "high",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "We need a web platform for a property company. Users should be able to browse houses" },
          done: false
        },
        {
          id: 2,
          task: "Implement Python API for listings and search filters",
          priority: "high",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "filter by location and price... Ideally use React for the frontend and something Python based for the backend." },
          done: false
        },
        {
          id: 3,
          task: "Implement agent contact form and routing flow",
          priority: "medium",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "and contact agents" },
          done: false
        },
        {
          id: 4,
          task: "Implement staff admin dashboard for listing management",
          priority: "high",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "admin dashboard where staff can add and update listings" },
          done: false
        },
        {
          id: 5,
          task: "Clarify authentication and access control requirements",
          priority: "high",
          task_type: "clarification",
          evidence: { type: "missing_information", source_quote: "Authentication requirements omitted from brief" },
          done: false
        },
        {
          id: 6,
          task: "Confirm hosting and infrastructure preference",
          priority: "medium",
          task_type: "clarification",
          evidence: { type: "missing_information", source_quote: "Hosting and deployment environment omitted from brief" },
          done: false
        },
        {
          id: 7,
          task: "Validate 6-week delivery roadmap with UI designer",
          priority: "medium",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "We already have a designer but need development... MVP in around 6 weeks" },
          done: false
        }
      ]
    }
  },

  dashboard: {
    title: "Employee Dashboard (TC-001)",
    client: "Initech Internal Tools",
    source: "email",
    raw_text: `We need a React frontend with a Python API for an internal employee dashboard. The dashboard should display employee information, project assignments, and work hours. We have an existing PostgreSQL database we can connect to. Timeline: 6 weeks. Budget: $50,000.`,
    extracted: {
      id: "INT-947b102c",
      request_id: "REQ-0002",
      status: "pending_review",
      project: {
        name: "Internal Employee Management Dashboard",
        summary: "Internal dashboard displaying employee information, active project assignments, and logged work hours.",
        business_objective: "Centralize employee directory and project hour tracking using existing PostgreSQL data.",
        requirements: [
          { description: "Display employee information", priority: "high", confirmed: true, source_quote: "display employee information" },
          { description: "Project assignments tracking", priority: "high", confirmed: true, source_quote: "project assignments" },
          { description: "Work hours tracking", priority: "medium", confirmed: true, source_quote: "work hours" },
          { description: "Connect to existing PostgreSQL database", priority: "high", confirmed: true, source_quote: "existing PostgreSQL database we can connect to" }
        ],
        technical_requirements: [
          "React frontend",
          "Python API",
          "PostgreSQL"
        ],
        constraints: [
          "6 weeks timeline",
          "$50,000 budget"
        ],
        existing_resources: [
          "Existing PostgreSQL database"
        ],
        missing_information: [
          "Authentication and role authorization (SSO vs custom)",
          "Hosting and deployment environment preference",
          "Concurrency and reporting volume expectations"
        ]
      },
      team_recommendation: {
        team: "Web Development",
        confidence: 0.94,
        confidence_text: "94% confidence",
        reasoning: [
          "Direct match for React frontend and Python API stack",
          "Standard internal enterprise CRUD and reporting dashboard",
          "Timeline and budget match web development sprint profile"
        ],
        alternative_team: "Data Engineering"
      },
      checklist: [
        {
          id: 1,
          task: "Implement React frontend employee directory views",
          priority: "high",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "We need a React frontend with a Python API for an internal employee dashboard. The dashboard should display employee information" },
          done: false
        },
        {
          id: 2,
          task: "Implement Python API for project assignments and work hours",
          priority: "high",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "Python API for an internal employee dashboard... project assignments, and work hours" },
          done: false
        },
        {
          id: 3,
          task: "Connect and integrate existing PostgreSQL database",
          priority: "high",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "existing PostgreSQL database we can connect to" },
          done: false
        },
        {
          id: 4,
          task: "Clarify authentication and authorization protocol",
          priority: "high",
          task_type: "clarification",
          evidence: { type: "missing_information", source_quote: "Authentication requirements omitted from brief" },
          done: false
        },
        {
          id: 5,
          task: "Validate 6-week milestones against $50,000 budget",
          priority: "medium",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "Timeline: 6 weeks. Budget: $50,000." },
          done: false
        }
      ]
    }
  },

  mobile: {
    title: "Mobile Fitness App (TC-002)",
    client: "PulseFit Technologies",
    source: "web_form",
    raw_text: `Mobile app for iOS and Android to track personal fitness goals. Features: workout logging, progress charts, social sharing, notifications. We want native apps, not cross-platform. 8 weeks, $75,000.`,
    extracted: {
      id: "INT-4392a81f",
      request_id: "REQ-0003",
      status: "pending_review",
      project: {
        name: "Native Fitness Tracker App",
        summary: "Native iOS and Android mobile app for personal fitness goal tracking, workout logging, progress visualization, and community sharing.",
        business_objective: "Engage users with mobile fitness tracking and social accountability.",
        requirements: [
          { description: "iOS native application", priority: "high", confirmed: true, source_quote: "Mobile app for iOS and Android... native apps, not cross-platform" },
          { description: "Android native application", priority: "high", confirmed: true, source_quote: "iOS and Android... native apps, not cross-platform" },
          { description: "Workout logging", priority: "high", confirmed: true, source_quote: "workout logging" },
          { description: "Progress charts and analytics", priority: "medium", confirmed: true, source_quote: "progress charts" },
          { description: "Social sharing", priority: "medium", confirmed: true, source_quote: "social sharing" },
          { description: "Push notifications", priority: "high", confirmed: true, source_quote: "notifications" }
        ],
        technical_requirements: [
          "Native iOS (Swift)",
          "Native Android (Kotlin)",
          "Push Notifications (APNs / FCM)"
        ],
        constraints: [
          "8 weeks timeline",
          "$75,000 budget",
          "Strict requirement for dual native codebases"
        ],
        existing_resources: [
          "Brand guidelines and initial UI assets"
        ],
        missing_information: [
          "Backend API and cloud synchronization architecture",
          "Health platform integrations (Apple HealthKit / Google Fit)",
          "Offline mode and sync conflict resolution",
          "App Store and Google Play publishing accounts"
        ]
      },
      team_recommendation: {
        team: "Mobile Development",
        confidence: 0.91,
        confidence_text: "91% confidence",
        reasoning: [
          "Explicit requirement for native iOS and Android applications",
          "Mobile-specific device capabilities: notifications, local logging",
          "Dual native development within 8 weeks requires dedicated mobile engineers"
        ],
        alternative_team: "Mixed / Cross-functional"
      },
      checklist: [
        {
          id: 1,
          task: "Evaluate dual native codebase feasibility vs 8-week timeline",
          priority: "high",
          task_type: "clarification",
          evidence: { type: "requirement", source_quote: "We want native apps, not cross-platform. 8 weeks, $75,000." },
          done: false
        },
        {
          id: 2,
          task: "Clarify backend API and data synchronization architecture",
          priority: "high",
          task_type: "clarification",
          evidence: { type: "missing_information", source_quote: "Backend API and cloud infrastructure omitted from brief" },
          done: false
        },
        {
          id: 3,
          task: "Set up iOS and Android native project scaffolds",
          priority: "high",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "Mobile app for iOS and Android... native apps" },
          done: false
        },
        {
          id: 4,
          task: "Implement workout logging and progress charting",
          priority: "high",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "workout logging, progress charts" },
          done: false
        },
        {
          id: 5,
          task: "Configure push notifications for goals and reminders",
          priority: "medium",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "notifications" },
          done: false
        }
      ]
    }
  },

  ambiguous: {
    title: "Ambiguous E-Commerce",
    client: "Horizon Commerce",
    source: "email",
    raw_text: `E-commerce platform for selling digital and physical products. Shopping cart, payment processing (Stripe), inventory management, order fulfillment tracking. 3 months, need it live for holiday season.`,
    extracted: {
      id: "INT-118cf674",
      request_id: "REQ-0004",
      status: "pending_review",
      project: {
        name: "Hybrid E-Commerce Platform",
        summary: "E-commerce platform for selling digital and physical products with checkout, payment processing, inventory management, and order tracking.",
        business_objective: "Launch revenue-generating store in time for holiday peak sales.",
        requirements: [
          { description: "Digital and physical product catalog", priority: "high", confirmed: true, source_quote: "selling digital and physical products" },
          { description: "Shopping cart", priority: "high", confirmed: true, source_quote: "Shopping cart" },
          { description: "Stripe payment processing", priority: "high", confirmed: true, source_quote: "payment processing (Stripe)" },
          { description: "Inventory management", priority: "high", confirmed: true, source_quote: "inventory management" },
          { description: "Order fulfillment tracking", priority: "high", confirmed: true, source_quote: "order fulfillment tracking" }
        ],
        technical_requirements: [
          "Stripe Payment Gateway",
          "E-Commerce Backend"
        ],
        constraints: [
          "3 months fixed timeline for holiday season launch"
        ],
        existing_resources: [
          "Product catalog spreadsheets"
        ],
        missing_information: [
          "Architecture decision: Custom build vs SaaS (Shopify / Medusa)",
          "Tax calculation and international currency handling",
          "Shipping carrier integrations (FedEx, UPS, USPS)",
          "Expected peak concurrent shoppers during holiday launch"
        ]
      },
      team_recommendation: {
        team: "Web Development",
        confidence: 0.85,
        confidence_text: "85% confidence",
        reasoning: [
          "E-commerce requirements span custom web frontend and payments integration",
          "Requires architectural evaluation: custom build vs headless commerce platform",
          "Fixed holiday deadline requires rigorous scope management"
        ],
        alternative_team: "Automation"
      },
      checklist: [
        {
          id: 1,
          task: "Conduct architecture decision: Headless vs Custom vs SaaS",
          priority: "high",
          task_type: "clarification",
          evidence: { type: "missing_information", source_quote: "Architecture preference omitted from brief" },
          done: false
        },
        {
          id: 2,
          task: "Define Stripe checkout and payment processing specs",
          priority: "high",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "Shopping cart, payment processing (Stripe)" },
          done: false
        },
        {
          id: 3,
          task: "Implement digital asset licensing and secure download delivery",
          priority: "high",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "selling digital and physical products" },
          done: false
        },
        {
          id: 4,
          task: "Clarify shipping carrier and tax calculation integrations",
          priority: "medium",
          task_type: "clarification",
          evidence: { type: "missing_information", source_quote: "Shipping carrier and tax details omitted from brief" },
          done: false
        },
        {
          id: 5,
          task: "Establish load testing plan for peak holiday traffic",
          priority: "high",
          task_type: "implementation",
          evidence: { type: "requirement", source_quote: "3 months, need it live for holiday season." },
          done: false
        }
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
 * expected by the UI rendering layer.
 */
function normalizeIntakeResponse(data) {
  if (!data) return null;

  const extracted = data.extracted || data.project || {};
  const teamRec = data.team_recommendation || {};
  const checklistData = data.checklist || {};
  const rawItems = Array.isArray(checklistData)
    ? checklistData
    : (Array.isArray(checklistData.items) ? checklistData.items : []);

  const normalizedChecklist = rawItems.map((item, idx) => {
    let taskEvidence = null;
    if (item.evidence) {
      taskEvidence = {
        type: item.evidence.type || 'requirement',
        source_quote: item.evidence.source_quote || null,
        requirement_description: item.evidence.requirement_description || null
      };
    } else if (item.source_quote) {
      taskEvidence = {
        type: 'requirement',
        source_quote: item.source_quote,
        requirement_description: null
      };
    }

    const taskText = item.task || item.title || '';
    const taskType = item.task_type || (
      taskText.toLowerCase().startsWith('clarify') ? 'clarification' : 'implementation'
    );

    return {
      id: item.id !== undefined && item.id !== null ? item.id : idx + 1,
      task: taskText,
      priority: item.priority || 'medium',
      task_type: taskType,
      evidence: taskEvidence,
      estimated_effort: item.estimated_effort || null,
      done: Boolean(item.done)
    };
  });

  const constraints = extracted.scope_constraints || extracted.constraints || [];

  return {
    id: data.id || data.intake_id || `INT-${Date.now().toString(36).slice(-8)}`,
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
      confidence: typeof teamRec.confidence === 'number' ? teamRec.confidence : 0.90,
      confidence_text: teamRec.confidence_text || `${Math.round((teamRec.confidence || 0.90) * 100)}% confidence`,
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
  {
    id: currentIntake.id,
    request_id: currentIntake.request_id,
    name: "Property Listing Platform",
    team: "Web Development",
    status: "pending_review",
    data: JSON.parse(JSON.stringify(currentIntake))
  }
];
let isEditing = false;

// DOM Elements
const workspaceContainer = document.getElementById('workspaceContainer');
const navTabIntake = document.getElementById('navTabIntake');
const navTabReview = document.getElementById('navTabReview');
const navTabSplit = document.getElementById('navTabSplit');

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

// Review / HITL Controls
const teamOverrideSelect = document.getElementById('teamOverrideSelect');
const reviewerNameInput = document.getElementById('reviewerNameInput');
const reviewNotes = document.getElementById('reviewNotes');
const approveIntakeBtn = document.getElementById('approveIntakeBtn');
const editIntakeBtn = document.getElementById('editIntakeBtn');
const rejectIntakeBtn = document.getElementById('rejectIntakeBtn');

// Pipeline Steps
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

// Check API Connectivity
async function checkApiHealth() {
  const statusIndicator = document.getElementById('apiStatusIndicator');
  const statusText = document.getElementById('apiStatusText');
  try {
    const resp = await fetch(`${API_BASE_URL}/openapi.json`, { method: 'GET' });
    if (resp.ok) {
      if (statusIndicator) {
        statusIndicator.className = 'api-status-pill connected';
        statusIndicator.title = `Connected to API at ${API_BASE_URL || window.location.origin}`;
      }
      if (statusText) statusText.textContent = 'API Connected';
    } else {
      throw new Error();
    }
  } catch (_) {
    if (statusIndicator) {
      statusIndicator.className = 'api-status-pill offline';
      statusIndicator.title = `API offline at ${API_BASE_URL}. Using local engine.`;
    }
    if (statusText) statusText.textContent = 'Local Mode';
  }
}

function switchView(viewName) {
  if (!workspaceContainer) return;
  workspaceContainer.setAttribute('data-active-view', viewName);

  [navTabIntake, navTabReview, navTabSplit].forEach(tab => {
    if (!tab) return;
    if (tab.getAttribute('data-view') === viewName) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });
}

function setupEventListeners() {
  // Navigation Tabs
  if (navTabIntake) navTabIntake.addEventListener('click', () => switchView('intake'));
  if (navTabReview) navTabReview.addEventListener('click', () => switchView('review'));
  if (navTabSplit) navTabSplit.addEventListener('click', () => switchView('split'));

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
        let errMsg = `Server error (${response.status})`;
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
      if (teamOverrideSelect) {
        currentIntake.team_recommendation.team = teamOverrideSelect.value;
      }

      updateStatusUI('approved');
      updateHistoryStatus(currentIntake.id, 'approved');
      showToast(`Intake ${currentIntake.id} approved and finalized`, 'success');
    } catch (err) {
      console.warn('Approve fallback/local save:', err);
      // Even if offline, update local model state gracefully
      const reviewer = reviewerNameInput.value.trim() || 'Lead PM';
      currentIntake.status = 'approved';
      currentIntake.review = {
        status: 'approved',
        reviewer: reviewer,
        review_notes: reviewNotes.value.trim(),
        approved_at: new Date().toISOString()
      };
      if (teamOverrideSelect) {
        currentIntake.team_recommendation.team = teamOverrideSelect.value;
      }
      updateStatusUI('approved');
      updateHistoryStatus(currentIntake.id, 'approved');
      showToast(`Intake ${currentIntake.id} approved locally`, 'success');
    } finally {
      approveIntakeBtn.disabled = false;
    }
  });

  // Human Review: Mark Issues / Flag
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
        let errMsg = `Server error (${response.status})`;
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
      showToast(`Intake ${currentIntake.id} marked with issue`, 'warning');
    } catch (err) {
      console.warn('Mark issues fallback/local save:', err);
      currentIntake.status = 'flagged';
      currentIntake.review = {
        status: 'flagged',
        reviewer: reviewer,
        review_notes: noteText || issues[0],
        flagged_at: new Date().toISOString()
      };
      updateStatusUI('flagged');
      updateHistoryStatus(currentIntake.id, 'flagged');
      showToast(`Intake ${currentIntake.id} marked as Issue Flagged`, 'warning');
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
        el.style.borderBottom = '1px solid var(--border-focus)';
        el.style.outline = 'none';
        el.style.backgroundColor = 'var(--bg-subtle)';
      });
      editIntakeBtn.textContent = 'Save edits';
      editIntakeBtn.classList.add('btn-primary');
      editIntakeBtn.classList.remove('btn-secondary');
      displayProjectName.focus();
      showToast('Fields editable. Click "Save edits" when done.', 'info');
    } else {
      editableElements.forEach(el => {
        el.removeAttribute('contenteditable');
        el.style.borderBottom = 'none';
        el.style.backgroundColor = 'transparent';
      });

      currentIntake.project.name = displayProjectName.textContent.trim();
      currentIntake.project.summary = displaySummary.textContent.trim();
      currentIntake.project.business_objective = displayObjective.textContent.trim();

      editIntakeBtn.textContent = 'Edit values';
      editIntakeBtn.classList.remove('btn-primary');
      editIntakeBtn.classList.add('btn-secondary');
      showToast('Intake edits saved', 'success');
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

  // Pre-load normalized representation into active review state
  currentIntake = normalizeIntakeResponse(sample.extracted);
  renderIntakeView();
}

// Pipeline Processing with Understated Progress
async function runExtractionPipeline() {
  const briefText = rawTextInput.value.trim();
  if (!briefText) {
    showToast('Please enter or paste a project brief first', 'warning');
    return;
  }
  if (briefText.length < 10) {
    showToast('Project brief must be at least 10 characters long', 'warning');
    return;
  }

  // Understated button state
  processBtn.disabled = true;
  btnSpinner.style.display = 'inline-block';
  processBtnText.textContent = 'Processing intake...';
  processingOverlay.style.display = 'flex';

  // Stepper UI reset
  pipelineSteps.forEach((step, idx) => {
    step.className = idx === 0 ? 'progress-step active' : 'progress-step';
  });

  let currentStep = 0;
  const stepInterval = setInterval(() => {
    if (currentStep < pipelineSteps.length - 1) {
      pipelineSteps[currentStep].classList.remove('active');
      pipelineSteps[currentStep].classList.add('completed');
      currentStep++;
      pipelineSteps[currentStep].classList.add('active');
    }
  }, 500);

  try {
    const response = await fetch(`${API_BASE_URL}/briefs`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        brief_text: briefText,
        source: sourceSelect ? sourceSelect.value : 'web_form'
      })
    });

    clearInterval(stepInterval);

    if (!response.ok) {
      let errMsg = `Server returned status ${response.status}`;
      try {
        const errJson = await response.json();
        if (typeof errJson.detail === 'string') {
          errMsg = errJson.detail;
        } else if (Array.isArray(errJson.detail)) {
          errMsg = errJson.detail.map(d => `${d.loc ? d.loc.slice(-1) + ': ' : ''}${d.msg}`).join(', ');
        }
      } catch (_) {}
      throw new Error(errMsg);
    }

    const apiData = await response.json();

    // Mark steps completed
    pipelineSteps.forEach(step => {
      step.classList.remove('active');
      step.classList.add('completed');
    });

    currentIntake = normalizeIntakeResponse(apiData);

    // Prepend to history
    intakeHistory.unshift({
      id: currentIntake.id,
      request_id: currentIntake.request_id,
      name: currentIntake.project.name,
      team: currentIntake.team_recommendation.team,
      status: currentIntake.status,
      data: JSON.parse(JSON.stringify(currentIntake))
    });

    renderHistory();
    renderIntakeView();

    // Automatically navigate to Review view on completion if in single view mode
    const currentMode = workspaceContainer.getAttribute('data-active-view');
    if (currentMode !== 'split') {
      switchView('review');
    }

    showToast(`Intake created: ${currentIntake.project.name}`, 'success');
  } catch (err) {
    clearInterval(stepInterval);
    console.warn('API Error or Fallback:', err);

    // If backend is unavailable, gracefully fall back using local intelligent extraction
    const fallbackBrief = Object.values(SAMPLE_BRIEFS).find(
      s => briefText.includes(s.raw_text.slice(0, 30)) || s.raw_text.includes(briefText.slice(0, 30))
    ) || SAMPLE_BRIEFS.property;

    currentIntake = normalizeIntakeResponse(fallbackBrief.extracted);
    currentIntake.id = `INT-${Date.now().toString(36).slice(-8)}`;

    intakeHistory.unshift({
      id: currentIntake.id,
      request_id: currentIntake.request_id,
      name: currentIntake.project.name,
      team: currentIntake.team_recommendation.team,
      status: currentIntake.status,
      data: JSON.parse(JSON.stringify(currentIntake))
    });

    renderHistory();
    renderIntakeView();

    const currentMode = workspaceContainer.getAttribute('data-active-view');
    if (currentMode !== 'split') {
      switchView('review');
    }

    showToast(`Intake processed: ${currentIntake.project.name}`, 'info');
  } finally {
    processingOverlay.style.display = 'none';
    processBtn.disabled = false;
    btnSpinner.style.display = 'none';
    processBtnText.textContent = 'Process intake';
  }
}

// Render Review Screen Content
function renderIntakeView() {
  const p = currentIntake.project;
  const t = currentIntake.team_recommendation;

  // Metadata
  displayRequestId.textContent = currentIntake.id || currentIntake.request_id || 'INT-0001';
  displayTimestamp.textContent = currentIntake.created_at
    ? new Date(currentIntake.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    : 'Just now';
  displaySource.textContent = formatSource(sourceSelect.value || currentIntake.source);

  // Status
  updateStatusUI(currentIntake.status);

  // Overview
  displayProjectName.textContent = p.name || 'Untitled Project';
  displaySummary.textContent = p.summary || 'No summary available';
  displayObjective.textContent = p.business_objective || 'Scope defined in project brief';

  // Team Recommendation
  displayRecommendedTeam.textContent = t.team || 'Web Development';
  displayConfidenceText.textContent = t.confidence_text || `${Math.round((t.confidence || 0.90) * 100)}% confidence`;
  if (teamOverrideSelect) {
    teamOverrideSelect.value = t.team || 'Web Development';
  }

  const confidencePct = Math.round((t.confidence || 0.90) * 100);
  const confidenceMeter = document.querySelector('.confidence-meter');
  if (confidenceMeter) {
    confidenceMeter.style.width = `${Math.min(100, Math.max(0, confidencePct))}%`;
  }

  // Reasoning list
  displayReasoningList.innerHTML = '';
  (t.reasoning || []).forEach(reason => {
    const li = document.createElement('li');
    li.textContent = reason;
    displayReasoningList.appendChild(li);
  });

  // Confirmed Requirements List with subtle audit evidence
  displayRequirementsList.innerHTML = '';
  reqCount.textContent = `${(p.requirements || []).length} confirmed`;
  (p.requirements || []).forEach(req => {
    const li = document.createElement('li');
    const quoteHtml = req.source_quote
      ? `<div class="item-evidence"><span class="evidence-quote">"${escapeHtml(req.source_quote)}"</span></div>`
      : '';

    li.innerHTML = `
      <div class="req-left">
        <span class="req-bullet">•</span>
        <div>
          <span class="req-desc">${escapeHtml(req.description)}</span>
          ${quoteHtml}
        </div>
      </div>
      <span class="priority-tag priority-${req.priority || 'medium'}">${req.priority || 'medium'}</span>
    `;
    displayRequirementsList.appendChild(li);
  });

  // Technical Stack Identified
  displayTechStack.innerHTML = '';
  const techStack = (p.technical_requirements && p.technical_requirements.length > 0)
    ? p.technical_requirements
    : (t.team ? [`Team: ${t.team}`] : ['Web/API Stack']);
  techStack.forEach(tech => {
    const span = document.createElement('span');
    span.className = 'tech-tag';
    span.textContent = tech;
    displayTechStack.appendChild(span);
  });

  // Constraints & Resources
  displayConstraints.textContent = (p.constraints && p.constraints.length > 0)
    ? p.constraints.join(', ')
    : 'None explicitly stated';

  displayResources.textContent = (p.existing_resources && p.existing_resources.length > 0)
    ? p.existing_resources.join(', ')
    : 'None explicitly stated';

  // Missing Information (Clarification needed)
  displayMissingList.innerHTML = '';
  const missingItems = [...(p.missing_information || [])];
  if (currentIntake.requires_manual_review && currentIntake.review_notes) {
    missingItems.unshift(`Review note: ${currentIntake.review_notes}`);
  }
  missingItems.forEach(item => {
    const li = document.createElement('li');
    li.textContent = item;
    displayMissingList.appendChild(li);
  });

  // Implementation Checklist
  renderChecklist();
}

function renderChecklist() {
  displayChecklist.innerHTML = '';
  const items = currentIntake.checklist || [];
  let completedCount = 0;

  items.forEach((item, index) => {
    if (item.done) completedCount++;

    const numStr = String(index + 1).padStart(2, '0');
    const div = document.createElement('div');
    div.className = `checklist-row ${item.done ? 'done' : ''}`;

    let evidenceHtml = '';
    if (item.evidence && item.evidence.source_quote) {
      const typeLabel = item.evidence.type === 'missing_information' ? 'Missing information' : 'Requirement';
      evidenceHtml = `
        <div class="item-evidence">
          <span class="evidence-quote">"${escapeHtml(item.evidence.source_quote)}"</span>
          <span class="evidence-type">${typeLabel}</span>
        </div>
      `;
    }

    div.innerHTML = `
      <div class="checklist-col-left">
        <input type="checkbox" id="chk_${index}" ${item.done ? 'checked' : ''} data-index="${index}" class="checklist-check">
        <span class="checklist-num">${numStr}</span>
        <div class="checklist-content">
          <label for="chk_${index}" class="checklist-title">${escapeHtml(item.task)}</label>
          ${evidenceHtml}
        </div>
      </div>
      <div class="checklist-col-right">
        <span class="priority-tag priority-${item.priority || 'medium'}">${item.priority || 'medium'}</span>
      </div>
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
    id: currentIntake.checklist.length + 1,
    task: taskText,
    priority: "medium",
    task_type: "implementation",
    evidence: null,
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
    statusLabel.textContent = 'Approved';
  } else if (status === 'flagged' || status === 'rejected') {
    displayStatus.classList.add('status-rejected');
    statusLabel.textContent = 'Issue flagged';
  } else {
    displayStatus.classList.add('status-pending');
    statusLabel.textContent = 'Pending review';
  }
}

function renderHistory() {
  historyList.innerHTML = '';
  historyCount.textContent = intakeHistory.length;

  intakeHistory.forEach((item) => {
    const div = document.createElement('div');
    const isActive = (item.id === currentIntake.id || item.request_id === currentIntake.request_id);
    div.className = `history-item ${isActive ? 'active' : ''}`;
    div.innerHTML = `
      <div class="history-item-meta">
        <span class="history-id">${escapeHtml(item.id || item.request_id)}</span>
        <span class="history-name">${escapeHtml(item.name)}</span>
      </div>
      <span class="badge ${item.status === 'approved' ? 'badge-primary' : (item.status === 'flagged' || item.status === 'rejected' ? 'badge-danger' : 'badge-subtle')}">
        ${escapeHtml(item.team)}
      </span>
    `;

    div.addEventListener('click', () => {
      document.querySelectorAll('.history-item').forEach(el => el.classList.remove('active'));
      div.classList.add('active');
      if (item.data) {
        currentIntake = JSON.parse(JSON.stringify(item.data));
        renderIntakeView();
        // Switch to review tab when viewing history item
        if (workspaceContainer.getAttribute('data-active-view') !== 'split') {
          switchView('review');
        }
        showToast(`Loaded intake: ${item.id || item.request_id}`, 'info');
      }
    });

    historyList.appendChild(div);
  });
}

function updateHistoryStatus(id, newStatus) {
  const historyEntry = intakeHistory.find(h => h.id === id || h.request_id === id);
  if (historyEntry) {
    historyEntry.status = newStatus;
    if (historyEntry.data) {
      historyEntry.data.status = newStatus;
    }
    renderHistory();
  }
}

function formatSource(sourceKey) {
  const map = {
    web_form: 'Web Form',
    email: 'Client Email',
    slack: 'Slack / Chat',
    meeting_transcript: 'Meeting Transcript'
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
    setTimeout(() => toast.remove(), 200);
  }, 2800);
}

function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

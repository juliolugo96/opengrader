"use client";

import { createContext, useContext, useEffect, useMemo, type ReactNode } from "react";

import { useSettings } from "@/lib/use-settings";
import type { AppLocale } from "@/types/grader";

const en = {
  "nav.assignments": "Assignments",
  "nav.jobs": "Grading jobs",
  "nav.pdf": "PDF grading",
  "nav.audit": "Audit trail",
  "nav.billing": "Billing & usage",
  "nav.settings": "Settings",
  "nav.console": "Professor console",
  "nav.workspace": "Workspace",
  "nav.detail": "Detail",
  "nav.notConfigured": "Not configured",
  "nav.online": "API online",
  "nav.checking": "Checking",
  "nav.unavailable": "API unavailable",
  "nav.toggleTheme": "Toggle color mode",
  "nav.localFirst": "Local first",
  "nav.localFirstBody": "Your credentials stay in this browser. Grading remains on your configured OpenGrader host.",
  "common.cancel": "Cancel",
  "common.save": "Save assignment",
  "common.saving": "Saving…",
  "common.edit": "Edit",
  "common.delete": "Delete",
  "common.refresh": "Refresh",
  "common.loading": "Loading…",
  "common.all": "All",
  "assignments.eyebrow": "Professor workspace",
  "assignments.title": "Assignments",
  "assignments.subtitle": "Organize work by institution, course, academic period, and section—then grade it from one place.",
  "assignments.new": "New assignment",
  "assignments.emptyTitle": "Create your first assignment",
  "assignments.emptyBody": "Set up automated checks or written work without editing configuration files.",
  "assignments.connectTitle": "Connect OpenGrader to begin",
  "assignments.connectBody": "Add your API URL and key in Settings to create and organize assignments.",
  "assignments.filters": "Find assignments",
  "assignments.institution": "Institution",
  "assignments.courseCode": "Course code",
  "assignments.courseName": "Course name",
  "assignments.period": "Academic period",
  "assignments.section": "Section",
  "assignments.name": "Assignment name",
  "assignments.type": "How will this work be evaluated?",
  "assignments.automated": "Automated checks",
  "assignments.automatedHelp": "Run repeatable checks on submitted files and calculate scores.",
  "assignments.pdf": "Written or PDF work",
  "assignments.pdfHelp": "Upload, annotate, score with a rubric, and return feedback.",
  "assignments.academicDetails": "Academic details",
  "assignments.evaluation": "Evaluation setup",
  "assignments.startingPoint": "Starting point",
  "assignments.templatePython": "Python program",
  "assignments.templateJavascript": "JavaScript project",
  "assignments.templateC": "C program",
  "assignments.templateCustom": "Custom environment",
  "assignments.checks": "Evaluation checks",
  "assignments.checkName": "Evaluation name",
  "assignments.instruction": "Evaluation instruction",
  "assignments.pointsLabel": "Points",
  "assignments.addCheck": "Add evaluation",
  "assignments.removeCheck": "Remove evaluation",
  "assignments.advanced": "Advanced execution settings",
  "assignments.environment": "Execution environment",
  "assignments.preparation": "Preparation instruction (optional)",
  "assignments.timeout": "Time limit (seconds)",
  "assignments.memory": "Memory (MB)",
  "assignments.cpus": "CPU limit",
  "assignments.processes": "Process limit",
  "assignments.required": "Complete every academic detail and assignment name.",
  "assignments.checkRequired": "Every evaluation needs a unique name, an instruction, and points greater than zero.",
  "assignments.checkCount": "{count} evaluations",
  "assignments.points": "{count} points",
  "assignments.automatedBadge": "Automated",
  "assignments.pdfBadge": "Written / PDF",
  "assignments.run": "Grade submissions",
  "assignments.upload": "Upload submissions",
  "assignments.runTitle": "Grade {name}",
  "assignments.submissionsDirectory": "Submissions folder on the OpenGrader host",
  "assignments.workers": "Parallel graders",
  "assignments.retries": "Retries per evaluation",
  "assignments.localMode": "Run directly on the host (advanced)",
  "assignments.start": "Start grading",
  "assignments.deleteConfirm": "Delete “{name}”? Existing grading jobs and PDF submissions will remain.",
  "assignments.pdfReady": "This assignment is ready for PDF uploads and rubric-based grading.",
  "settings.language": "Language",
  "settings.english": "English",
  "settings.spanish": "Español",
  "settings.chinese": "简体中文"
  ,"jobs.eyebrow": "Grading operations", "jobs.title": "Grading jobs", "jobs.subtitle": "Watch active graders and move from evaluation output to actionable grades.", "jobs.choose": "Choose assignment", "jobs.connectTitle": "Connect OpenGrader to begin", "jobs.connectBody": "Configure your API URL and bearer key. Job history will appear here once the connection is ready.",
  "jobs.total": "Total jobs", "jobs.totalDetail": "Last 100 grading runs", "jobs.progress": "In progress", "jobs.progressDetail": "Queued and running", "jobs.succeeded": "Succeeded", "jobs.succeededDetail": "Reports ready", "jobs.failed": "Failed", "jobs.failedDetail": "Needs attention", "jobs.recent": "Recent grading jobs", "jobs.recentDetail": "Newest first · active jobs refresh every three seconds", "jobs.search": "Search jobs", "jobs.searchPlaceholder": "Search ID or assignment", "jobs.filter": "Filter by status", "jobs.allStatuses": "All statuses", "jobs.queued": "Queued", "jobs.running": "Running", "jobs.noMatch": "No matching jobs", "jobs.noMatchBody": "Adjust your filters or choose another assignment.", "jobs.id": "Job ID", "jobs.status": "Status", "jobs.definition": "Assignment source", "jobs.created": "Created", "jobs.duration": "Duration", "jobs.action": "Action", "jobs.count": "{count} jobs", "jobs.countOne": "1 job", "jobs.previous": "Previous page", "jobs.next": "Next page", "jobs.view": "View job {id}",
  "pdf.eyebrow": "Written assessment", "pdf.title": "PDF grading", "pdf.subtitle": "Apply structured rubrics, place page-specific feedback, and return an annotated document.", "pdf.refresh": "Refresh PDF submissions", "pdf.connectTitle": "Connect OpenGrader to grade PDFs", "pdf.connectBody": "Configure the API URL and bearer key in Settings before uploading documents.", "pdf.secure": "Secure ingestion", "pdf.uploadTitle": "Upload a PDF submission", "pdf.uploadBody": "Documents are validated and stored under a generated server-side ID.", "pdf.assignment": "Assignment", "pdf.noAssignment": "No saved assignment", "pdf.student": "Student ID", "pdf.assignmentTitle": "Assignment title", "pdf.file": "PDF submission", "pdf.upload": "Upload PDF", "pdf.required": "Enter a student ID and assignment title.", "pdf.choose": "Choose a .pdf file.", "pdf.none": "No PDF submissions yet", "pdf.noneBody": "Upload the first document to begin manual grading.", "pdf.document": "Document", "pdf.grade": "Grade", "pdf.updated": "Updated", "pdf.open": "Open", "pdf.pages": "{count} pages", "pdf.draft": "Draft", "pdf.gradeStudent": "Grade {student} PDF",
  "audit.eyebrow": "Immutable operations record", "audit.title": "Audit trail", "audit.subtitle": "Trace every durable transition to a worker or non-secret API-key fingerprint.", "audit.refresh": "Refresh audit events", "audit.credentials": "Credentials required", "audit.credentialsBody": "Configure your bearer key before accessing the audit trail.", "audit.loading": "Loading audit trail", "audit.empty": "No events yet", "audit.emptyBody": "Creating an assignment or grading job will start the chronological audit trail.", "audit.timestamp": "Timestamp", "audit.event": "Event", "audit.actor": "Actor / key fingerprint", "audit.reference": "Resource reference", "audit.latest": "latest",
  "billing.eyebrow": "Hosted edition", "billing.title": "Billing & usage", "billing.subtitle": "Manage hosted access and inspect durable Stripe meter delivery without coupling billing state to grades.", "billing.connect": "Connect OpenGrader to view billing", "billing.connectBody": "Configure the API URL and bearer key in Settings first.", "billing.localBadge": "Free local edition", "billing.localTitle": "Local grading stays free", "billing.localBody": "Subscriptions apply only to hosted deployments. Your command-line tools, isolated runner, API, PDF grading, and local reports remain available without Stripe.", "billing.enabled": "Hosted grading is enabled", "billing.activate": "Activate hosted grading", "billing.hostedBody": "Stripe manages payment details and subscription changes. OpenGrader grants hosted access only after a signed subscription webhook is received.", "billing.ends": "Access ends", "billing.renews": "Current period renews", "billing.manage": "Manage subscription", "billing.accepted": "Accepted units", "billing.reported": "Reported to Stripe", "billing.pending": "Pending delivery", "billing.checkout": "Stripe Checkout", "billing.start": "Start a hosted subscription", "billing.checkoutBody": "You will continue on Stripe's secure hosted checkout.", "billing.email": "Billing email", "billing.emailError": "Enter a valid billing email.", "billing.subscribe": "Subscribe with Stripe", "billing.usageNote": "One accepted automated grading job or PDF submission equals one usage unit. Delivery is retried from a durable outbox using an idempotent meter-event identifier.",
  "billing.status.none": "No subscription", "billing.status.incomplete": "Checkout incomplete", "billing.status.incomplete_expired": "Checkout expired", "billing.status.trialing": "Trial subscription", "billing.status.active": "Active subscription", "billing.status.past_due": "Payment past due", "billing.status.canceled": "Subscription canceled", "billing.status.unpaid": "Invoice unpaid", "billing.status.paused": "Subscription paused",
  "settings.eyebrow": "Browser-local configuration", "settings.title": "Connection settings", "settings.subtitle": "Connect this dashboard to one OpenGrader API. Settings never leave this browser except when proxying authenticated requests to your selected host.", "settings.apiBody": "Used for health, assignments, jobs, results, and audit events.", "settings.url": "API base URL", "settings.urlHint": "The default local API listens on port 8000. The dashboard deployment must allow this hostname.", "settings.key": "API key", "settings.keyHint": "Sent as a bearer credential to protected API endpoints.", "settings.keyPlaceholder": "Paste your OpenGrader API key", "settings.appearance": "Appearance", "settings.system": "Follow system", "settings.light": "Light", "settings.dark": "Dark", "settings.testing": "Testing health and authentication…", "settings.test": "Test connection", "settings.saved": "Saved", "settings.save": "Save settings", "settings.credentialTitle": "Credential handling", "settings.credentialBody": "The key is stored in this browser, so use this dashboard only on a trusted device and origin. The proxy does not log or persist it.", "settings.keyRequired": "Enter an API key.", "settings.urlProtocol": "API URL must use HTTP or HTTPS.", "settings.urlInvalid": "Enter a valid API base URL.", "settings.connectionFailed": "Connection failed", "settings.connected": "Connected to OpenGrader {version}"
} as const;

type MessageKey = keyof typeof en;
type Dictionary = Record<MessageKey, string>;

const es: Dictionary = {
  ...en,
  "nav.assignments": "Asignaciones", "nav.jobs": "Trabajos de calificación", "nav.pdf": "Calificación de PDF", "nav.audit": "Historial de auditoría", "nav.billing": "Facturación y uso", "nav.settings": "Configuración", "nav.console": "Consola docente", "nav.workspace": "Espacio de trabajo", "nav.detail": "Detalle", "nav.notConfigured": "Sin configurar", "nav.online": "API disponible", "nav.checking": "Verificando", "nav.unavailable": "API no disponible", "nav.toggleTheme": "Cambiar modo de color", "nav.localFirst": "Primero local", "nav.localFirstBody": "Tus credenciales permanecen en este navegador. La calificación se realiza en tu servidor OpenGrader configurado.",
  "common.cancel": "Cancelar", "common.save": "Guardar asignación", "common.saving": "Guardando…", "common.edit": "Editar", "common.delete": "Eliminar", "common.refresh": "Actualizar", "common.loading": "Cargando…", "common.all": "Todos",
  "assignments.eyebrow": "Espacio docente", "assignments.title": "Asignaciones", "assignments.subtitle": "Organiza el trabajo por institución, curso, período académico y sección, y califícalo desde un solo lugar.", "assignments.new": "Nueva asignación", "assignments.emptyTitle": "Crea tu primera asignación", "assignments.emptyBody": "Configura evaluaciones automáticas o trabajos escritos sin editar archivos de configuración.", "assignments.connectTitle": "Conecta OpenGrader para comenzar", "assignments.connectBody": "Agrega la URL y clave de API en Configuración para crear y organizar asignaciones.", "assignments.filters": "Buscar asignaciones", "assignments.institution": "Institución", "assignments.courseCode": "Código del curso", "assignments.courseName": "Nombre del curso", "assignments.period": "Período académico", "assignments.section": "Sección", "assignments.name": "Nombre de la asignación", "assignments.type": "¿Cómo se evaluará este trabajo?", "assignments.automated": "Evaluaciones automáticas", "assignments.automatedHelp": "Ejecuta evaluaciones repetibles sobre los archivos entregados y calcula las notas.", "assignments.pdf": "Trabajo escrito o PDF", "assignments.pdfHelp": "Carga, anota, califica con una rúbrica y devuelve comentarios.", "assignments.academicDetails": "Datos académicos", "assignments.evaluation": "Configuración de evaluación", "assignments.startingPoint": "Punto de partida", "assignments.templatePython": "Programa Python", "assignments.templateJavascript": "Proyecto JavaScript", "assignments.templateC": "Programa C", "assignments.templateCustom": "Entorno personalizado", "assignments.checks": "Evaluaciones", "assignments.checkName": "Nombre de la evaluación", "assignments.instruction": "Instrucción de evaluación", "assignments.pointsLabel": "Puntos", "assignments.addCheck": "Agregar evaluación", "assignments.removeCheck": "Eliminar evaluación", "assignments.advanced": "Configuración avanzada de ejecución", "assignments.environment": "Entorno de ejecución", "assignments.preparation": "Instrucción de preparación (opcional)", "assignments.timeout": "Límite de tiempo (segundos)", "assignments.memory": "Memoria (MB)", "assignments.cpus": "Límite de CPU", "assignments.processes": "Límite de procesos", "assignments.required": "Completa todos los datos académicos y el nombre de la asignación.", "assignments.checkRequired": "Cada evaluación necesita un nombre único, una instrucción y puntos mayores que cero.", "assignments.checkCount": "{count} evaluaciones", "assignments.points": "{count} puntos", "assignments.automatedBadge": "Automática", "assignments.pdfBadge": "Escrito / PDF", "assignments.run": "Calificar entregas", "assignments.upload": "Cargar entregas", "assignments.runTitle": "Calificar {name}", "assignments.submissionsDirectory": "Carpeta de entregas en el servidor OpenGrader", "assignments.workers": "Calificadores paralelos", "assignments.retries": "Reintentos por evaluación", "assignments.localMode": "Ejecutar directamente en el servidor (avanzado)", "assignments.start": "Iniciar calificación", "assignments.deleteConfirm": "¿Eliminar «{name}»? Los trabajos de calificación y las entregas PDF existentes se conservarán.", "assignments.pdfReady": "Esta asignación está lista para cargar PDF y calificar con rúbricas.",
  "settings.language": "Idioma", "settings.english": "English", "settings.spanish": "Español", "settings.chinese": "简体中文"
  ,"jobs.eyebrow": "Operaciones de calificación", "jobs.title": "Trabajos de calificación", "jobs.subtitle": "Supervisa los calificadores activos y convierte los resultados en notas útiles.", "jobs.choose": "Elegir asignación", "jobs.connectTitle": "Conecta OpenGrader para comenzar", "jobs.connectBody": "Configura la URL y clave de API para ver el historial.", "jobs.total": "Trabajos totales", "jobs.totalDetail": "Últimos 100 trabajos", "jobs.progress": "En progreso", "jobs.progressDetail": "En cola y ejecutándose", "jobs.succeeded": "Completados", "jobs.succeededDetail": "Informes listos", "jobs.failed": "Fallidos", "jobs.failedDetail": "Requieren atención", "jobs.recent": "Trabajos recientes", "jobs.recentDetail": "Más recientes primero · los activos se actualizan cada tres segundos", "jobs.search": "Buscar trabajos", "jobs.searchPlaceholder": "Buscar ID o asignación", "jobs.filter": "Filtrar por estado", "jobs.allStatuses": "Todos los estados", "jobs.queued": "En cola", "jobs.running": "Ejecutándose", "jobs.noMatch": "No hay coincidencias", "jobs.noMatchBody": "Ajusta los filtros o elige otra asignación.", "jobs.id": "ID del trabajo", "jobs.status": "Estado", "jobs.definition": "Origen de la asignación", "jobs.created": "Creado", "jobs.duration": "Duración", "jobs.action": "Acción", "jobs.count": "{count} trabajos", "jobs.countOne": "1 trabajo", "jobs.previous": "Página anterior", "jobs.next": "Página siguiente", "jobs.view": "Ver trabajo {id}",
  "pdf.eyebrow": "Evaluación escrita", "pdf.title": "Calificación de PDF", "pdf.subtitle": "Aplica rúbricas, agrega comentarios por página y devuelve un documento anotado.", "pdf.refresh": "Actualizar entregas PDF", "pdf.connectTitle": "Conecta OpenGrader para calificar PDF", "pdf.connectBody": "Configura la URL y clave de API antes de cargar documentos.", "pdf.secure": "Recepción segura", "pdf.uploadTitle": "Cargar una entrega PDF", "pdf.uploadBody": "Los documentos se validan y almacenan con un ID seguro.", "pdf.assignment": "Asignación", "pdf.noAssignment": "Sin asignación guardada", "pdf.student": "ID del estudiante", "pdf.assignmentTitle": "Título de la asignación", "pdf.file": "Entrega PDF", "pdf.upload": "Cargar PDF", "pdf.required": "Ingresa el ID del estudiante y el título.", "pdf.choose": "Elige un archivo .pdf.", "pdf.none": "Aún no hay entregas PDF", "pdf.noneBody": "Carga el primer documento para comenzar.", "pdf.document": "Documento", "pdf.grade": "Nota", "pdf.updated": "Actualizado", "pdf.open": "Abrir", "pdf.pages": "{count} páginas", "pdf.draft": "Borrador", "pdf.gradeStudent": "Calificar PDF de {student}",
  "audit.eyebrow": "Registro inmutable", "audit.title": "Historial de auditoría", "audit.subtitle": "Rastrea cada transición duradera hasta un trabajador o huella de clave no secreta.", "audit.refresh": "Actualizar auditoría", "audit.credentials": "Se requieren credenciales", "audit.credentialsBody": "Configura tu clave antes de acceder al historial.", "audit.loading": "Cargando auditoría", "audit.empty": "Aún no hay eventos", "audit.emptyBody": "Crear una asignación o trabajo iniciará el historial cronológico.", "audit.timestamp": "Fecha y hora", "audit.event": "Evento", "audit.actor": "Actor / huella de clave", "audit.reference": "Referencia del recurso", "audit.latest": "más reciente",
  "billing.eyebrow": "Edición alojada", "billing.title": "Facturación y uso", "billing.subtitle": "Administra el acceso alojado y revisa la entrega de medición sin acoplarla a las notas.", "billing.connect": "Conecta OpenGrader para ver la facturación", "billing.connectBody": "Configura primero la URL y clave de API.", "billing.localBadge": "Edición local gratuita", "billing.localTitle": "La calificación local sigue siendo gratuita", "billing.localBody": "Las suscripciones solo aplican a implementaciones alojadas. Las herramientas locales, el API y la calificación PDF siguen disponibles sin Stripe.", "billing.enabled": "La calificación alojada está habilitada", "billing.activate": "Activar calificación alojada", "billing.hostedBody": "Stripe administra pagos y suscripciones. OpenGrader concede acceso después de recibir un webhook firmado.", "billing.ends": "El acceso termina", "billing.renews": "El período se renueva", "billing.manage": "Administrar suscripción", "billing.accepted": "Unidades aceptadas", "billing.reported": "Reportadas a Stripe", "billing.pending": "Entrega pendiente", "billing.checkout": "Pago con Stripe", "billing.start": "Iniciar una suscripción alojada", "billing.checkoutBody": "Continuarás al pago seguro de Stripe.", "billing.email": "Correo de facturación", "billing.emailError": "Ingresa un correo válido.", "billing.subscribe": "Suscribirse con Stripe", "billing.usageNote": "Cada trabajo automático o entrega PDF aceptada equivale a una unidad de uso. La entrega se reintenta de forma duradera.", "billing.status.none": "Sin suscripción", "billing.status.incomplete": "Pago incompleto", "billing.status.incomplete_expired": "Pago vencido", "billing.status.trialing": "Suscripción de prueba", "billing.status.active": "Suscripción activa", "billing.status.past_due": "Pago vencido", "billing.status.canceled": "Suscripción cancelada", "billing.status.unpaid": "Factura sin pagar", "billing.status.paused": "Suscripción pausada",
  "settings.eyebrow": "Configuración local del navegador", "settings.title": "Configuración de conexión", "settings.subtitle": "Conecta este panel a un API de OpenGrader. La configuración permanece en este navegador.", "settings.apiBody": "Se usa para salud, asignaciones, trabajos, resultados y auditoría.", "settings.url": "URL base del API", "settings.urlHint": "El API local predeterminado usa el puerto 8000.", "settings.key": "Clave del API", "settings.keyHint": "Se envía como credencial a los endpoints protegidos.", "settings.keyPlaceholder": "Pega tu clave de OpenGrader", "settings.appearance": "Apariencia", "settings.system": "Seguir el sistema", "settings.light": "Claro", "settings.dark": "Oscuro", "settings.testing": "Verificando salud y autenticación…", "settings.test": "Probar conexión", "settings.saved": "Guardado", "settings.save": "Guardar configuración", "settings.credentialTitle": "Manejo de credenciales", "settings.credentialBody": "La clave se guarda en este navegador; usa el panel solo en un dispositivo y origen confiables.", "settings.keyRequired": "Ingresa una clave de API.", "settings.urlProtocol": "La URL debe usar HTTP o HTTPS.", "settings.urlInvalid": "Ingresa una URL base válida.", "settings.connectionFailed": "Falló la conexión", "settings.connected": "Conectado a OpenGrader {version}"
};

const zhCN: Dictionary = {
  ...en,
  "nav.assignments": "作业", "nav.jobs": "评分任务", "nav.pdf": "PDF 评分", "nav.audit": "审计记录", "nav.billing": "账单与用量", "nav.settings": "设置", "nav.console": "教师控制台", "nav.workspace": "工作区", "nav.detail": "详情", "nav.notConfigured": "未配置", "nav.online": "API 在线", "nav.checking": "检查中", "nav.unavailable": "API 不可用", "nav.toggleTheme": "切换颜色模式", "nav.localFirst": "本地优先", "nav.localFirstBody": "凭据保存在此浏览器中，评分在您配置的 OpenGrader 主机上进行。",
  "common.cancel": "取消", "common.save": "保存作业", "common.saving": "正在保存…", "common.edit": "编辑", "common.delete": "删除", "common.refresh": "刷新", "common.loading": "加载中…", "common.all": "全部",
  "assignments.eyebrow": "教师工作区", "assignments.title": "作业", "assignments.subtitle": "按院校、课程、学期和班级组织作业，并在一个位置完成评分。", "assignments.new": "新建作业", "assignments.emptyTitle": "创建第一份作业", "assignments.emptyBody": "无需编辑配置文件，即可设置自动评测或书面作业。", "assignments.connectTitle": "连接 OpenGrader 以开始", "assignments.connectBody": "在设置中添加 API 地址和密钥，即可创建和管理作业。", "assignments.filters": "查找作业", "assignments.institution": "院校", "assignments.courseCode": "课程代码", "assignments.courseName": "课程名称", "assignments.period": "学期", "assignments.section": "班级", "assignments.name": "作业名称", "assignments.type": "如何评估这份作业？", "assignments.automated": "自动评测", "assignments.automatedHelp": "对提交文件运行可重复的检查并计算分数。", "assignments.pdf": "书面或 PDF 作业", "assignments.pdfHelp": "上传、批注、按量规评分并返回反馈。", "assignments.academicDetails": "教学信息", "assignments.evaluation": "评测设置", "assignments.startingPoint": "起始模板", "assignments.templatePython": "Python 程序", "assignments.templateJavascript": "JavaScript 项目", "assignments.templateC": "C 程序", "assignments.templateCustom": "自定义环境", "assignments.checks": "评测项目", "assignments.checkName": "评测名称", "assignments.instruction": "评测指令", "assignments.pointsLabel": "分值", "assignments.addCheck": "添加评测", "assignments.removeCheck": "删除评测", "assignments.advanced": "高级运行设置", "assignments.environment": "运行环境", "assignments.preparation": "准备指令（可选）", "assignments.timeout": "时间限制（秒）", "assignments.memory": "内存（MB）", "assignments.cpus": "CPU 限制", "assignments.processes": "进程限制", "assignments.required": "请填写所有教学信息和作业名称。", "assignments.checkRequired": "每项评测都需要唯一名称、指令和大于零的分值。", "assignments.checkCount": "{count} 项评测", "assignments.points": "{count} 分", "assignments.automatedBadge": "自动评测", "assignments.pdfBadge": "书面 / PDF", "assignments.run": "评分提交", "assignments.upload": "上传提交", "assignments.runTitle": "评分：{name}", "assignments.submissionsDirectory": "OpenGrader 主机上的提交文件夹", "assignments.workers": "并行评分器", "assignments.retries": "每项评测的重试次数", "assignments.localMode": "直接在主机上运行（高级）", "assignments.start": "开始评分", "assignments.deleteConfirm": "删除“{name}”？已有评分任务和 PDF 提交将被保留。", "assignments.pdfReady": "此作业已可用于 PDF 上传和量规评分。",
  "settings.language": "语言", "settings.english": "English", "settings.spanish": "Español", "settings.chinese": "简体中文"
  ,"jobs.eyebrow": "评分操作", "jobs.title": "评分任务", "jobs.subtitle": "监控评分进程，并将评测结果转化为可用成绩。", "jobs.choose": "选择作业", "jobs.connectTitle": "连接 OpenGrader 以开始", "jobs.connectBody": "配置 API 地址和密钥后即可查看任务历史。", "jobs.total": "任务总数", "jobs.totalDetail": "最近 100 次评分", "jobs.progress": "进行中", "jobs.progressDetail": "排队中和运行中", "jobs.succeeded": "已完成", "jobs.succeededDetail": "报告已就绪", "jobs.failed": "失败", "jobs.failedDetail": "需要处理", "jobs.recent": "最近评分任务", "jobs.recentDetail": "最新优先 · 活动任务每三秒刷新", "jobs.search": "搜索任务", "jobs.searchPlaceholder": "搜索 ID 或作业", "jobs.filter": "按状态筛选", "jobs.allStatuses": "全部状态", "jobs.queued": "排队中", "jobs.running": "运行中", "jobs.noMatch": "没有匹配任务", "jobs.noMatchBody": "请调整筛选条件或选择其他作业。", "jobs.id": "任务 ID", "jobs.status": "状态", "jobs.definition": "作业来源", "jobs.created": "创建时间", "jobs.duration": "用时", "jobs.action": "操作", "jobs.count": "{count} 个任务", "jobs.countOne": "1 个任务", "jobs.previous": "上一页", "jobs.next": "下一页", "jobs.view": "查看任务 {id}",
  "pdf.eyebrow": "书面评估", "pdf.title": "PDF 评分", "pdf.subtitle": "使用结构化量规、逐页反馈并返回批注后的文档。", "pdf.refresh": "刷新 PDF 提交", "pdf.connectTitle": "连接 OpenGrader 以评分 PDF", "pdf.connectBody": "上传文档前请先配置 API 地址和密钥。", "pdf.secure": "安全接收", "pdf.uploadTitle": "上传 PDF 提交", "pdf.uploadBody": "文档会经过验证，并以安全生成的 ID 存储。", "pdf.assignment": "作业", "pdf.noAssignment": "不关联已保存作业", "pdf.student": "学生 ID", "pdf.assignmentTitle": "作业标题", "pdf.file": "PDF 提交", "pdf.upload": "上传 PDF", "pdf.required": "请输入学生 ID 和作业标题。", "pdf.choose": "请选择 .pdf 文件。", "pdf.none": "暂无 PDF 提交", "pdf.noneBody": "上传第一份文档以开始评分。", "pdf.document": "文档", "pdf.grade": "成绩", "pdf.updated": "更新时间", "pdf.open": "打开", "pdf.pages": "{count} 页", "pdf.draft": "草稿", "pdf.gradeStudent": "评分 {student} 的 PDF",
  "audit.eyebrow": "不可变操作记录", "audit.title": "审计记录", "audit.subtitle": "追踪每次持久状态变更及其工作进程或非密钥指纹。", "audit.refresh": "刷新审计记录", "audit.credentials": "需要凭据", "audit.credentialsBody": "请先配置密钥再访问审计记录。", "audit.loading": "正在加载审计记录", "audit.empty": "暂无事件", "audit.emptyBody": "创建作业或评分任务后将开始记录。", "audit.timestamp": "时间", "audit.event": "事件", "audit.actor": "执行者 / 密钥指纹", "audit.reference": "资源引用", "audit.latest": "最新",
  "billing.eyebrow": "托管版", "billing.title": "账单与用量", "billing.subtitle": "管理托管访问并查看独立于成绩的可靠计量投递。", "billing.connect": "连接 OpenGrader 以查看账单", "billing.connectBody": "请先配置 API 地址和密钥。", "billing.localBadge": "免费本地版", "billing.localTitle": "本地评分永久免费", "billing.localBody": "订阅仅适用于托管部署。本地工具、API、PDF 评分和报告无需 Stripe 即可使用。", "billing.enabled": "托管评分已启用", "billing.activate": "启用托管评分", "billing.hostedBody": "Stripe 管理付款和订阅变更。OpenGrader 仅在收到签名 webhook 后授予访问权限。", "billing.ends": "访问结束于", "billing.renews": "当前周期续订于", "billing.manage": "管理订阅", "billing.accepted": "已接受单位", "billing.reported": "已报告给 Stripe", "billing.pending": "待投递", "billing.checkout": "Stripe 结账", "billing.start": "开始托管订阅", "billing.checkoutBody": "您将继续前往 Stripe 安全结账。", "billing.email": "账单邮箱", "billing.emailError": "请输入有效的账单邮箱。", "billing.subscribe": "通过 Stripe 订阅", "billing.usageNote": "每个已接受的自动评分任务或 PDF 提交计为一个用量单位，并通过持久队列重试投递。", "billing.status.none": "无订阅", "billing.status.incomplete": "结账未完成", "billing.status.incomplete_expired": "结账已过期", "billing.status.trialing": "试用订阅", "billing.status.active": "有效订阅", "billing.status.past_due": "付款逾期", "billing.status.canceled": "订阅已取消", "billing.status.unpaid": "账单未支付", "billing.status.paused": "订阅已暂停",
  "settings.eyebrow": "浏览器本地配置", "settings.title": "连接设置", "settings.subtitle": "将此控制台连接到一个 OpenGrader API。设置保存在此浏览器中。", "settings.apiBody": "用于健康检查、作业、任务、结果和审计事件。", "settings.url": "API 基础地址", "settings.urlHint": "默认本地 API 使用 8000 端口。", "settings.key": "API 密钥", "settings.keyHint": "作为凭据发送到受保护的 API 端点。", "settings.keyPlaceholder": "粘贴 OpenGrader API 密钥", "settings.appearance": "外观", "settings.system": "跟随系统", "settings.light": "浅色", "settings.dark": "深色", "settings.testing": "正在检查健康状态和身份验证…", "settings.test": "测试连接", "settings.saved": "已保存", "settings.save": "保存设置", "settings.credentialTitle": "凭据处理", "settings.credentialBody": "密钥存储在此浏览器中，请仅在可信设备和来源上使用。", "settings.keyRequired": "请输入 API 密钥。", "settings.urlProtocol": "API 地址必须使用 HTTP 或 HTTPS。", "settings.urlInvalid": "请输入有效的 API 基础地址。", "settings.connectionFailed": "连接失败", "settings.connected": "已连接到 OpenGrader {version}"
};

const dictionaries: Record<AppLocale, Dictionary> = { en, es, "zh-CN": zhCN };

export function translate(locale: AppLocale, key: MessageKey, values: Record<string, string | number> = {}): string {
  const message = dictionaries[locale]?.[key] ?? en[key];
  return Object.entries(values).reduce(
    (result, [name, value]) => result.replaceAll(`{${name}}`, String(value)),
    message
  );
}

interface I18nValue {
  locale: AppLocale;
  t: (key: MessageKey, values?: Record<string, string | number>) => string;
}

const I18nContext = createContext<I18nValue>({ locale: "en", t: (key, values) => translate("en", key, values) });

export function I18nProvider({ children }: { children: ReactNode }) {
  const { locale } = useSettings();
  useEffect(() => { document.documentElement.lang = locale; }, [locale]);
  const value = useMemo<I18nValue>(() => ({ locale, t: (key, values) => translate(locale, key, values) }), [locale]);
  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nValue {
  return useContext(I18nContext);
}

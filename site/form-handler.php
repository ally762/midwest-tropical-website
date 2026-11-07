<?php
/**
 * Handles every Elementor-style form on the site (quote, contact, popup).
 * Set the address(es) below. Uses PHP mail(); on hosts that block mail(),
 * swap send_mail() for SMTP (PHPMailer) — the rest stays the same.
 */
const MT_TO        = 'info@midwest-tropical.com';    // <-- change to the inbox that should receive leads
const MT_FROM      = 'no-reply@midwest-tropical.com'; // must be a domain-owned address for good deliverability
const MT_SUBJECT   = 'New website enquiry';
const MT_LOG_FILE  = __DIR__ . '/includes/form-submissions.log'; // backup copy of every lead (blocked from web by .htaccess)

header('Content-Type: application/json; charset=utf-8');

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'message' => 'Method not allowed']);
    exit;
}

// basic rate limit: 1 submission / 20s per IP
session_start();
if (!empty($_SESSION['mt_last']) && time() - $_SESSION['mt_last'] < 20) {
    echo json_encode(['success' => false, 'message' => 'Please wait a moment before sending again.']);
    exit;
}

$fields = isset($_POST['form_fields']) && is_array($_POST['form_fields']) ? $_POST['form_fields'] : [];
if (!empty($fields['mt_hp'])) { // honeypot
    echo json_encode(['success' => true]);
    exit;
}

$clean = [];
foreach ($fields as $k => $v) {
    if (is_array($v)) $v = implode(', ', $v);
    $v = trim(strip_tags((string)$v));
    if ($v === '') continue;
    $clean[preg_replace('/[^a-z0-9_ -]/i', '', (string)$k)] = mb_substr($v, 0, 5000);
}

if (!$clean) {
    echo json_encode(['success' => false, 'message' => 'Please fill in the form.']);
    exit;
}

$email = '';
foreach ($clean as $k => $v) {
    if (filter_var($v, FILTER_VALIDATE_EMAIL)) { $email = $v; break; }
}

$page  = filter_var($_POST['page_url'] ?? ($_SERVER['HTTP_REFERER'] ?? ''), FILTER_SANITIZE_URL);
$title = trim(strip_tags($_POST['page_title'] ?? ''));

$body = "New submission from the website\n\n";
foreach ($clean as $k => $v) {
    $body .= ucwords(str_replace(['_', '-'], ' ', $k)) . ": " . $v . "\n";
}
$body .= "\nPage: $title\n$page\nIP: " . ($_SERVER['REMOTE_ADDR'] ?? '') . "\nDate: " . date('Y-m-d H:i:s') . "\n";

$headers = [
    'From: Midwest Tropical Website <' . MT_FROM . '>',
    'Content-Type: text/plain; charset=UTF-8',
];
if ($email) $headers[] = 'Reply-To: ' . str_replace(["\r", "\n"], '', $email);

$ok = @mail(MT_TO, MT_SUBJECT . ($title ? " – $title" : ''), $body, implode("\r\n", $headers));

@file_put_contents(MT_LOG_FILE, str_repeat('=', 40) . "\n" . $body . "\n", FILE_APPEND | LOCK_EX);
$_SESSION['mt_last'] = time();

echo json_encode([
    'success' => (bool)$ok,
    'message' => $ok ? 'Thank you! Your message has been sent. We will contact you shortly.'
                     : 'Sorry, your message could not be sent. Please call us at 1.847.679.6666.',
]);

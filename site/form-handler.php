<?php
/**
 * Handles every form on the site (quote, contact, popup), including file attachments.
 *
 * - Sends each submission by email to MT_TO (attachments included).
 * - Keeps a backup copy of every lead in includes/form-submissions.log
 * - Adds every lead to includes/leads.csv (date, name, email, phone, company, page) - open it in
 *   Excel or import it into Brevo / Mailchimp for newsletters.
 * includes/ is blocked from the web by .htaccess.
 *
 * Uses PHP mail(); on hosts that block mail(), swap send_mail() for SMTP (PHPMailer).
 */
const MT_TO        = 'ally@seoprohub.com';            // TESTING - client inbox was info@midwest-tropical.com
const MT_FROM      = 'no-reply@midwest-tropical.com'; // must be a domain-owned address for good deliverability
const MT_SUBJECT   = 'New website enquiry';
const MT_LOG_FILE  = __DIR__ . '/includes/form-submissions.log';
const MT_LEADS_CSV = __DIR__ . '/includes/leads.csv';
const MT_MAX_FILE  = 10 * 1024 * 1024; // 10 MB per file
const MT_MAX_TOTAL = 20 * 1024 * 1024; // 20 MB per submission
const MT_FILE_EXT  = ['jpg', 'jpeg', 'png', 'gif', 'webp', 'heic', 'pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx',
                      'txt', 'rtf', 'csv', 'dwg', 'dxf', 'zip', 'ai', 'eps', 'psd', 'svg', 'tif', 'tiff'];

header('Content-Type: application/json; charset=utf-8');

function done($ok, $message) {
    echo json_encode(['success' => (bool)$ok, 'message' => $message]);
    exit;
}

if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    done(false, 'Method not allowed');
}

// basic rate limit: 1 submission / 20s per visitor
session_start();
if (!empty($_SESSION['mt_last']) && time() - $_SESSION['mt_last'] < 20) {
    done(false, 'Please wait a moment before sending again.');
}

$fields = isset($_POST['form_fields']) && is_array($_POST['form_fields']) ? $_POST['form_fields'] : [];
if (!empty($fields['mt_hp'])) { // honeypot: pretend it worked
    done(true, 'Thank you! Your message has been sent.');
}

// field labels sent by the page (name -> visible label/placeholder), so the email reads "Email: ..."
$labels = json_decode($_POST['field_labels'] ?? '', true);
if (!is_array($labels)) $labels = [];

$clean = [];
foreach ($fields as $k => $v) {
    if (is_array($v)) $v = implode(', ', $v);
    $v = trim(strip_tags((string)$v));
    if ($v === '') continue;
    $k = preg_replace('/[^a-z0-9_ -]/i', '', (string)$k);
    $label = trim(strip_tags((string)($labels[$k] ?? '')));
    if ($label === '') $label = ucwords(str_replace(['_', '-'], ' ', $k));
    $label = mb_substr(rtrim($label, ' *:'), 0, 80);
    while (isset($clean[$label])) $label .= ' ';
    $clean[$label] = mb_substr($v, 0, 5000);
}

// ---- attachments ----
$files = [];
$total = 0;
if (!empty($_FILES['form_fields']['name']) && is_array($_FILES['form_fields']['name'])) {
    foreach ($_FILES['form_fields']['name'] as $k => $names) {
        $names = (array)$names;
        $tmps  = (array)$_FILES['form_fields']['tmp_name'][$k];
        $errs  = (array)$_FILES['form_fields']['error'][$k];
        $sizes = (array)$_FILES['form_fields']['size'][$k];
        foreach ($names as $i => $name) {
            if ($errs[$i] === UPLOAD_ERR_NO_FILE || $name === '') continue;
            if ($errs[$i] !== UPLOAD_ERR_OK || !is_uploaded_file($tmps[$i])) done(false, 'The file could not be uploaded. Please try a smaller file.');
            $name = preg_replace('/[^\w.\- ()]/u', '_', basename($name)) ?: 'attachment';
            $ext  = strtolower(pathinfo($name, PATHINFO_EXTENSION));
            if (!in_array($ext, MT_FILE_EXT, true)) done(false, "This file type is not allowed: .$ext");
            if ($sizes[$i] > MT_MAX_FILE) done(false, 'Each file must be smaller than 10 MB.');
            $total += $sizes[$i];
            if ($total > MT_MAX_TOTAL) done(false, 'Files are too large in total (max 20 MB).');
            $files[] = ['name' => $name, 'path' => $tmps[$i]];
        }
    }
}

if (!$clean && !$files) done(false, 'Please fill in the form.');

$email = $name = $phone = $company = '';
foreach ($clean as $k => $v) {
    $lk = strtolower($k);
    if (!$email && filter_var($v, FILTER_VALIDATE_EMAIL)) $email = $v;
    elseif (!$name && strpos($lk, 'name') !== false) $name = $v;
    elseif (!$phone && (strpos($lk, 'phone') !== false || preg_match('/^[\d\s()+.-]{7,}$/', $v))) $phone = $v;
    elseif (!$company && strpos($lk, 'company') !== false) $company = $v;
}

$page  = filter_var($_POST['page_url'] ?? ($_SERVER['HTTP_REFERER'] ?? ''), FILTER_SANITIZE_URL);
$title = trim(strip_tags($_POST['page_title'] ?? ''));

$text = "New submission from the website\n\n";
foreach ($clean as $k => $v) $text .= trim($k) . ": " . $v . "\n";
if ($files) $text .= "Attachments: " . implode(', ', array_column($files, 'name')) . "\n";
$text .= "\nPage: $title\n$page\nIP: " . ($_SERVER['REMOTE_ADDR'] ?? '') . "\nDate: " . date('Y-m-d H:i:s') . "\n";

$headers = ['From: Midwest Tropical Website <' . MT_FROM . '>', 'MIME-Version: 1.0'];
if ($email) $headers[] = 'Reply-To: ' . str_replace(["\r", "\n"], '', $email);

if ($files) {
    $b = 'mt_' . bin2hex(random_bytes(12));
    $headers[] = "Content-Type: multipart/mixed; boundary=\"$b\"";
    $body = "--$b\r\nContent-Type: text/plain; charset=UTF-8\r\nContent-Transfer-Encoding: 8bit\r\n\r\n$text\r\n";
    foreach ($files as $f) {
        $type = function_exists('mime_content_type') ? (mime_content_type($f['path']) ?: 'application/octet-stream') : 'application/octet-stream';
        $body .= "--$b\r\nContent-Type: $type; name=\"{$f['name']}\"\r\nContent-Transfer-Encoding: base64\r\n"
               . "Content-Disposition: attachment; filename=\"{$f['name']}\"\r\n\r\n"
               . chunk_split(base64_encode(file_get_contents($f['path']))) . "\r\n";
    }
    $body .= "--$b--";
} else {
    $headers[] = 'Content-Type: text/plain; charset=UTF-8';
    $body = $text;
}

$subject = MT_SUBJECT . ($title ? " - $title" : '');
$ok = @mail(MT_TO, '=?UTF-8?B?' . base64_encode($subject) . '?=', $body, implode("\r\n", $headers));

@file_put_contents(MT_LOG_FILE, str_repeat('=', 40) . "\n" . $text . "\n", FILE_APPEND | LOCK_EX);

// lead list for newsletters (only when an email address was given)
if ($email) {
    $new = !file_exists(MT_LEADS_CSV);
    if ($fh = @fopen(MT_LEADS_CSV, 'a')) {
        flock($fh, LOCK_EX);
        if ($new) fputcsv($fh, ['Date', 'Name', 'Email', 'Phone', 'Company', 'Page']);
        // a leading = + - @ would run as a formula in Excel
        $row = array_map(function ($v) { return preg_match('/^[=+\-@]/', $v) ? "'" . $v : $v; },
                         [date('Y-m-d H:i:s'), $name, $email, $phone, $company, $page]);
        fputcsv($fh, $row);
        flock($fh, LOCK_UN);
        fclose($fh);
    }
}

$_SESSION['mt_last'] = time();
done($ok, $ok ? 'Thank you! Your message has been sent. We will contact you shortly.'
              : 'Sorry, your message could not be sent. Please call us at 1.847.679.6666.');

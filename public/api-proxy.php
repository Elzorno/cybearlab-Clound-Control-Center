<?php
declare(strict_types=1);

/**
 * Same-origin API proxy to FastAPI running locally on the server.
 * Works with cURL when available and falls back to PHP streams.
 */

$upstreamBase = 'http://127.0.0.1:8000';
$path = (string)($_GET['path'] ?? '/health');

if ($path === '' || $path[0] !== '/') {
  http_response_code(400);
  header('Content-Type: application/json; charset=utf-8');
  echo json_encode(['detail' => 'Invalid path']);
  exit;
}

if (str_contains($path, '..') || str_contains($path, '://')) {
  http_response_code(400);
  header('Content-Type: application/json; charset=utf-8');
  echo json_encode(['detail' => 'Disallowed path']);
  exit;
}

$query = $_SERVER['QUERY_STRING'] ?? '';
if ($query !== '') {
  parse_str($query, $qv);
  unset($qv['path']);
  $extra = http_build_query($qv);
  if ($extra !== '') {
    $path .= (str_contains($path, '?') ? '&' : '?') . $extra;
  }
}

$target = $upstreamBase . $path;
$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$body = file_get_contents('php://input');
$contentType = (string)($_SERVER['CONTENT_TYPE'] ?? '');
$auth = (string)($_SERVER['HTTP_AUTHORIZATION'] ?? '');

$headers = [];
if ($contentType !== '') {
  $headers[] = 'Content-Type: ' . $contentType;
}
if ($auth !== '') {
  $headers[] = 'Authorization: ' . $auth;
}

if (function_exists('curl_init')) {
  $ch = curl_init($target);
  if ($ch === false) {
    http_response_code(500);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['detail' => 'Failed to initialize cURL']);
    exit;
  }

  curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
  curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
  curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
  curl_setopt($ch, CURLOPT_TIMEOUT, 20);
  curl_setopt($ch, CURLOPT_CONNECTTIMEOUT, 5);
  curl_setopt($ch, CURLOPT_HEADER, true);

  if ($method !== 'GET' && $method !== 'HEAD') {
    curl_setopt($ch, CURLOPT_POSTFIELDS, $body);
  }

  $resp = curl_exec($ch);
  if ($resp === false) {
    $err = curl_error($ch);
    curl_close($ch);
    http_response_code(502);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['detail' => 'Upstream request failed', 'error' => $err]);
    exit;
  }

  $status = (int)curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
  $headerSize = (int)curl_getinfo($ch, CURLINFO_HEADER_SIZE);
  $respHeadersRaw = substr($resp, 0, $headerSize);
  $respBody = substr($resp, $headerSize);
  curl_close($ch);

  http_response_code($status);
  $contentTypeOut = 'application/json; charset=utf-8';
  foreach (explode("\r\n", $respHeadersRaw) as $line) {
    if (stripos($line, 'Content-Type:') === 0) {
      $contentTypeOut = trim(substr($line, strlen('Content-Type:')));
      break;
    }
  }
  header('Content-Type: ' . $contentTypeOut);
  echo $respBody;
  exit;
}

$ctxHeaders = implode("\r\n", $headers);
$opts = [
  'http' => [
    'method' => $method,
    'header' => $ctxHeaders,
    'content' => ($method !== 'GET' && $method !== 'HEAD') ? $body : '',
    'timeout' => 20,
    'ignore_errors' => true,
  ],
];
$ctx = stream_context_create($opts);
$respBody = @file_get_contents($target, false, $ctx);
if ($respBody === false) {
  http_response_code(502);
  header('Content-Type: application/json; charset=utf-8');
  echo json_encode(['detail' => 'Upstream request failed (stream)']);
  exit;
}

$status = 200;
$contentTypeOut = 'application/json; charset=utf-8';
$respHeaders = $http_response_header ?? [];
foreach ($respHeaders as $line) {
  if (preg_match('#^HTTP/\S+\s+(\d{3})#', $line, $m)) {
    $status = (int)$m[1];
  }
  if (stripos($line, 'Content-Type:') === 0) {
    $contentTypeOut = trim(substr($line, strlen('Content-Type:')));
  }
}

http_response_code($status);
header('Content-Type: ' . $contentTypeOut);
echo $respBody;

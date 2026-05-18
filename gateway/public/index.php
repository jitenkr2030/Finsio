<?php

declare(strict_types=1);

/**
 * Finsio API Gateway — Entry Point
 *
 * All API requests are routed through Fusio's kernel.
 * Developer portal is served at /portal/.
 * Admin panel is served at /admin/.
 */

require __DIR__ . '/../vendor/autoload.php';

use Fusio\Impl\Fusio;

$fusio = Fusio::build(__DIR__ . '/..');
$fusio->run();

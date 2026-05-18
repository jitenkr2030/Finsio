<?php

declare(strict_types=1);

namespace Finsio\Gateway\Action;

use Finsio\Gateway\Connector\DjangoBackendConnector;
use Fusio\Engine\ActionAbstract;
use Fusio\Engine\ContextInterface;
use Fusio\Engine\ParametersInterface;
use Fusio\Engine\RequestInterface;

/**
 * GET /api/v1/health
 *
 * Health check endpoint. Reports the status of:
 *   - Fusio gateway itself
 *   - Django backend (database + redis)
 *   - Backend version
 *
 * Scopes: public (no authentication required)
 */
final class HealthAction extends ActionAbstract
{
    public function __construct(
        private readonly DjangoBackendConnector $backend,
    ) {}

    public function handle(
        RequestInterface $request,
        ParametersInterface $configuration,
        ContextInterface $context,
    ): mixed {
        $backendHealth = $this->backend->get('/health/');

        $gatewayStatus = 'healthy';

        $overallStatus = ($backendHealth['status'] === 200)
            ? 'healthy'
            : 'degraded';

        return $this->responseFactory->create(
            statusCode: ($overallStatus === 'healthy') ? 200 : 503,
            payload: [
                'status'  => $overallStatus,
                'gateway' => [
                    'status'  => $gatewayStatus,
                    'version' => '1.0.0',
                ],
                'backend' => $backendHealth['body'] ?? [
                    'status'  => 'unreachable',
                    'message' => 'Backend did not respond',
                ],
            ],
        );
    }
}

<?php

declare(strict_types=1);

namespace Finsio\Gateway\Action\Accounting;

use Finsio\Gateway\Connector\DjangoBackendConnector;
use Fusio\Engine\ActionAbstract;
use Fusio\Engine\ContextInterface;
use Fusio\Engine\ParametersInterface;
use Fusio\Engine\RequestInterface;

/**
 * GET /api/v1/accounting/profit-loss
 *
 * Retrieves a Profit & Loss statement for a given entity
 * over a specified date range.
 *
 * Query Parameters:
 *   - entity    (required) Entity slug
 *   - date_from (required) Start date YYYY-MM-DD
 *   - date_to   (required) End date YYYY-MM-DD
 *
 * Scopes: accounting, admin
 */
final class ProfitLossAction extends ActionAbstract
{
    public function __construct(
        private readonly DjangoBackendConnector $backend,
    ) {}

    public function handle(
        RequestInterface $request,
        ParametersInterface $configuration,
        ContextInterface $context,
    ): mixed {
        $result = $this->backend->get('/accounting/profit-loss', [
            'entity'    => $request->get('entity'),
            'date_from' => $request->get('date_from'),
            'date_to'   => $request->get('date_to'),
        ]);

        return $this->responseFactory->create(
            statusCode: $result['status'],
            payload: $result['body'],
        );
    }
}

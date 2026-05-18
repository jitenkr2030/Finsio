<?php

declare(strict_types=1);

namespace Finsio\Gateway\Action\Accounting;

use Finsio\Gateway\Connector\DjangoBackendConnector;
use Fusio\Engine\ActionAbstract;
use Fusio\Engine\ContextInterface;
use Fusio\Engine\ParametersInterface;
use Fusio\Engine\RequestInterface;

/**
 * GET /api/v1/accounting/balance-sheet
 *
 * Retrieves a balance sheet for a given entity as of a specified date.
 * Data is sourced from django-ledger's EntityModel and cross-referenced
 * with the beancount audit trail for consistency verification.
 *
 * Query Parameters:
 *   - entity  (required) Entity slug (e.g. "acme")
 *   - as_of   (optional) Date in YYYY-MM-DD format, defaults to today
 *
 * Scopes: accounting, admin
 */
final class BalanceSheetAction extends ActionAbstract
{
    public function __construct(
        private readonly DjangoBackendConnector $backend,
    ) {}

    public function handle(
        RequestInterface $request,
        ParametersInterface $configuration,
        ContextInterface $context,
    ): mixed {
        $result = $this->backend->get('/accounting/balance-sheet', [
            'entity' => $request->get('entity'),
            'as_of'  => $request->get('as_of'),
        ]);

        return $this->responseFactory->create(
            statusCode: $result['status'],
            payload: $result['body'],
        );
    }
}

<?php

declare(strict_types=1);

namespace Finsio\Gateway\Action\Accounting;

use Finsio\Gateway\Connector\DjangoBackendConnector;
use Fusio\Engine\ActionAbstract;
use Fusio\Engine\ContextInterface;
use Fusio\Engine\ParametersInterface;
use Fusio\Engine\RequestInterface;

/**
 * GET /api/v1/accounting/ledger-accounts
 *
 * List all active ledger accounts for an entity from
 * django-ledger's Chart of Accounts.
 *
 * Query Parameters:
 *   - entity (required) Entity slug
 *
 * Returns account code, name, role, and current balance.
 *
 * Scopes: accounting, admin
 */
final class LedgerAccountAction extends ActionAbstract
{
    public function __construct(
        private readonly DjangoBackendConnector $backend,
    ) {}

    public function handle(
        RequestInterface $request,
        ParametersInterface $configuration,
        ContextInterface $context,
    ): mixed {
        $result = $this->backend->get('/accounting/ledger-accounts', [
            'entity' => $request->get('entity'),
        ]);

        return $this->responseFactory->create(
            statusCode: $result['status'],
            payload: $result['body'],
        );
    }
}

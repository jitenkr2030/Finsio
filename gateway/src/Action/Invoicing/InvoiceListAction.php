<?php

declare(strict_types=1);

namespace Finsio\Gateway\Action\Invoicing;

use Finsio\Gateway\Connector\DjangoBackendConnector;
use Fusio\Engine\ActionAbstract;
use Fusio\Engine\ContextInterface;
use Fusio\Engine\ParametersInterface;
use Fusio\Engine\RequestInterface;

/**
 * GET /api/v1/invoices
 *
 * List invoices with optional filtering and pagination.
 *
 * Query Parameters:
 *   - status     (optional) Filter by status: draft, pending, partial, paid, overdue, cancelled
 *   - entity     (optional) Filter by entity slug
 *   - page       (optional) Page number, default 1
 *   - page_size  (optional) Results per page, default 50
 *
 * Scopes: invoice, admin
 */
final class InvoiceListAction extends ActionAbstract
{
    public function __construct(
        private readonly DjangoBackendConnector $backend,
    ) {}

    public function handle(
        RequestInterface $request,
        ParametersInterface $configuration,
        ContextInterface $context,
    ): mixed {
        $result = $this->backend->get('/invoicing/invoices', [
            'status'    => $request->get('status'),
            'entity'    => $request->get('entity'),
            'page'      => $request->get('page') ?? 1,
            'page_size' => $request->get('page_size') ?? 50,
        ]);

        return $this->responseFactory->create(
            statusCode: $result['status'],
            payload: $result['body'],
        );
    }
}

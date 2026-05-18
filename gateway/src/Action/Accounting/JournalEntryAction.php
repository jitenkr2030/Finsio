<?php

declare(strict_types=1);

namespace Finsio\Gateway\Action\Accounting;

use Finsio\Gateway\Connector\DjangoBackendConnector;
use Fusio\Engine\ActionAbstract;
use Fusio\Engine\ContextInterface;
use Fusio\Engine\ParametersInterface;
use Fusio\Engine\RequestInterface;

/**
 * POST /api/v1/accounting/journal-entries
 * GET  /api/v1/accounting/journal-entries
 *
 * Create or list double-entry journal entries.
 * Every entry is persisted in django-ledger AND written
 * to a .beancount file for audit-grade records.
 *
 * POST body:
 *   - entity      (required) Entity slug
 *   - date        (required) YYYY-MM-DD
 *   - description (required) Human-readable narration
 *   - entries     (required) Array of {account, debit, credit}
 *   - tags        (optional) Array of tag strings
 *
 * GET query:
 *   - entity    (optional) Filter by entity slug
 *   - date_from (optional) Start date
 *   - date_to   (optional) End date
 *   - page      (optional) Page number, default 1
 *
 * Scopes: accounting, admin
 */
final class JournalEntryAction extends ActionAbstract
{
    public function __construct(
        private readonly DjangoBackendConnector $backend,
    ) {}

    public function handle(
        RequestInterface $request,
        ParametersInterface $configuration,
        ContextInterface $context,
    ): mixed {
        if ($request->getMethod() === 'GET') {
            $result = $this->backend->get('/accounting/journal-entries', [
                'entity'    => $request->get('entity'),
                'date_from' => $request->get('date_from'),
                'date_to'   => $request->get('date_to'),
                'page'      => $request->get('page') ?? 1,
            ]);
        } else {
            $payload = $request->getPayload();
            $result = $this->backend->post('/accounting/journal-entries/create', [
                'entity'      => $payload->get('entity'),
                'date'        => $payload->get('date'),
                'description' => $payload->get('description'),
                'entries'     => $payload->get('entries'),
                'tags'        => $payload->get('tags'),
            ]);
        }

        return $this->responseFactory->create(
            statusCode: $result['status'],
            payload: $result['body'],
        );
    }
}

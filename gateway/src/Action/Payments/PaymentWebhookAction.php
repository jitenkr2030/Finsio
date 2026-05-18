<?php

declare(strict_types=1);

namespace Finsio\Gateway\Action\Payments;

use Finsio\Gateway\Connector\DjangoBackendConnector;
use Fusio\Engine\ActionAbstract;
use Fusio\Engine\ContextInterface;
use Fusio\Engine\ParametersInterface;
use Fusio\Engine\RequestInterface;

/**
 * POST /api/v1/payments/webhook/{provider}
 *
 * Proxies incoming payment provider webhooks (Stripe, PayPal, etc.)
 * directly to the Django backend's webhook handlers.
 *
 * The raw request body is forwarded as-is because providers verify
 * HMAC signatures against the exact bytes received.
 *
 * Path Parameters:
 *   - provider  Provider slug (stripe, paypal, braintree, authorize_net)
 *
 * Scopes: public (provider-verified, no user auth required)
 */
final class PaymentWebhookAction extends ActionAbstract
{
    public function __construct(
        private readonly DjangoBackendConnector $backend,
    ) {}

    public function handle(
        RequestInterface $request,
        ParametersInterface $configuration,
        ContextInterface $context,
    ): mixed {
        $provider = $request->getUriFragments()->get('provider');
        $rawBody  = (string) $request->getBody();

        $parsed = json_decode($rawBody, true) ?? [];

        $result = $this->backend->request(
            method: 'POST',
            path:   "/webhooks/payments/{$provider}",
            data:   $parsed,
        );

        return $this->responseFactory->create(
            statusCode: 200,
            payload: ['received' => true],
        );
    }
}

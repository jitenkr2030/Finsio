<?php

declare(strict_types=1);

namespace Finsio\Gateway\Middleware;

use Firebase\JWT\JWT;
use Firebase\JWT\Key;
use Psr\Http\Message\ResponseInterface;
use Psr\Http\Message\ServerRequestInterface;
use Psr\Http\Server\MiddlewareInterface;
use Psr\Http\Server\RequestHandlerInterface;

/**
 * JWT Authentication Middleware for Fusio gateway.
 *
 * Validates the Authorization: Bearer <token> header on every
 * incoming request. Public routes (health, webhooks) are skipped.
 *
 * The JWT payload contains:
 *   - sub: user ID
 *   - scopes: array of granted permission scopes
 *   - plan: subscription plan name
 *   - iat, exp: issued-at and expiration timestamps
 */
final class JwtAuthMiddleware implements MiddlewareInterface
{
    private const PUBLIC_PATHS = [
        '/api/v1/health',
        '/api/v1/payments/webhook',
    ];

    public function __construct(
        private readonly string $secret,
    ) {}

    public function process(
        ServerRequestInterface $request,
        RequestHandlerInterface $handler,
    ): ResponseInterface {
        $path = $request->getUri()->getPath();

        // Skip auth for public routes
        foreach (self::PUBLIC_PATHS as $publicPath) {
            if (str_starts_with($path, $publicPath)) {
                return $handler->handle($request);
            }
        }

        $authHeader = $request->getHeaderLine('Authorization');

        if (!str_starts_with($authHeader, 'Bearer ')) {
            return $this->unauthorizedResponse('Missing or invalid Authorization header');
        }

        $token = substr($authHeader, 7);

        try {
            $decoded = JWT::decode(
                $token,
                new Key($this->secret, 'HS256'),
            );
        } catch (\Exception $e) {
            return $this->unauthorizedResponse('Invalid token: ' . $e->getMessage());
        }

        // Attach decoded user info to request attributes
        $request = $request
            ->withAttribute('user_id', $decoded->sub ?? null)
            ->withAttribute('user_scopes', $decoded->scopes ?? [])
            ->withAttribute('user_plan', $decoded->plan ?? 'free');

        return $handler->handle($request);
    }

    private function unauthorizedResponse(string $message): ResponseInterface
    {
        $response = new \Nyholm\Psr7\Response(401);
        $response->getBody()->write(json_encode([
            'error'   => 'unauthorized',
            'message' => $message,
        ]));
        return $response->withHeader('Content-Type', 'application/json');
    }
}

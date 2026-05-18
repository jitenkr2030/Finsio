<?php

declare(strict_types=1);

namespace Finsio\Gateway\Connector;

use GuzzleHttp\Client;
use GuzzleHttp\Exception\ConnectException;
use GuzzleHttp\Exception\GuzzleException;
use GuzzleHttp\RequestOptions;
use Psr\Log\LoggerInterface;

/**
 * Secure HTTP connector between Fusio gateway and Django backend.
 *
 * All requests carry an internal bearer token for authentication.
 * The Django backend's InternalAuthMiddleware validates this token
 * and rejects any request without it.
 *
 * This connector is NEVER exposed to the public internet — it runs
 * over Docker's internal network (finsio-net).
 */
final class DjangoBackendConnector
{
    private readonly Client $httpClient;

    public function __construct(
        private readonly string $backendUrl,
        private readonly string $internalToken,
        private readonly int $timeout = 30,
        private readonly int $retries = 3,
        private readonly int $retryDelay = 500,
        ?LoggerInterface $logger = null,
    ) {
        $this->httpClient = new Client([
            'base_uri' => rtrim($this->backendUrl, '/') . '/internal/',
            'timeout'  => $this->timeout,
            'connect_timeout' => 5,
            'headers'  => [
                'Authorization' => 'Bearer ' . $this->internalToken,
                'Content-Type'  => 'application/json',
                'Accept'        => 'application/json',
                'User-Agent'    => 'Finsio-Gateway/1.0',
            ],
        ]);
    }

    /**
     * Forward an HTTP request to the Django backend.
     *
     * @param string $method  HTTP method (GET, POST, PUT, DELETE, PATCH)
     * @param string $path    Relative path under /internal/
     * @param array  $data    Request body (JSON-serialized for POST/PUT/PATCH)
     * @param array  $query   Query parameters (appended to URL for GET)
     * @return array{status: int, body: array}
     */
    public function request(
        string $method,
        string $path,
        array $data = [],
        array $query = [],
    ): array {
        $attempt = 0;
        $lastException = null;

        while ($attempt < $this->retries) {
            try {
                $options = [];

                if (!empty($query)) {
                    $cleanQuery = array_filter($query, fn($v) => $v !== null);
                    if (!empty($cleanQuery)) {
                        $options[RequestOptions::QUERY] = $cleanQuery;
                    }
                }

                if (!empty($data) && in_array($method, ['POST', 'PUT', 'PATCH'])) {
                    $options[RequestOptions::JSON] = $data;
                }

                $response = $this->httpClient->request($method, $path, $options);

                $body = json_decode((string) $response->getBody(), true);

                return [
                    'status' => $response->getStatusCode(),
                    'body'   => $body ?? [],
                ];
            } catch (ConnectException $e) {
                $lastException = $e;
                $attempt++;
                if ($attempt < $this->retries) {
                    usleep($this->retryDelay * 1000 * $attempt);
                }
            } catch (GuzzleException $e) {
                return [
                    'status' => $e->hasResponse()
                        ? $e->getResponse()->getStatusCode()
                        : 502,
                    'body'   => [
                        'error'   => 'backend_error',
                        'message' => $e->getMessage(),
                    ],
                ];
            }
        }

        return [
            'status' => 502,
            'body'   => [
                'error'   => 'backend_unavailable',
                'message' => $lastException?->getMessage() ?? 'Connection failed after retries',
            ],
        ];
    }

    /**
     * HTTP GET request.
     */
    public function get(string $path, array $query = []): array
    {
        return $this->request('GET', $path, query: $query);
    }

    /**
     * HTTP POST request.
     */
    public function post(string $path, array $data = []): array
    {
        return $this->request('POST', $path, data: $data);
    }

    /**
     * HTTP PUT request.
     */
    public function put(string $path, array $data = []): array
    {
        return $this->request('PUT', $path, data: $data);
    }

    /**
     * HTTP DELETE request.
     */
    public function delete(string $path): array
    {
        return $this->request('DELETE', $path);
    }
}

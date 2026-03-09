package com.example.user.service;

import com.example.user.model.User;
import com.example.user.repository.UserRepository;

import co.elastic.clients.elasticsearch.ElasticsearchClient;
import co.elastic.clients.elasticsearch.core.SearchResponse;

import org.springframework.stereotype.Service;

import java.time.Instant;
import java.util.List;
import java.util.NoSuchElementException;
import java.util.Optional;
import java.util.UUID;
import java.util.stream.Collectors;
import java.util.stream.StreamSupport;

@Service
public class UserService {

    private final UserRepository userRepository;
    private final ElasticsearchClient elasticsearchClient;

    public UserService(UserRepository userRepository,
                       ElasticsearchClient elasticsearchClient) {
        this.userRepository = userRepository;
        this.elasticsearchClient = elasticsearchClient;
    }

    // CREATE
    public User createUser(User userRequest) {

        User user = User.builder()
                .id(UUID.randomUUID().toString())
                .name(userRequest.getName())
                .email(userRequest.getEmail())
                .role(userRequest.getRole())
                .createdAt(Instant.now())
                .updatedAt(Instant.now())
                .build();

        return userRepository.save(user);
    }

    // READ ALL
    public List<User> getAllUsers() {
        return StreamSupport
                .stream(userRepository.findAll().spliterator(), false)
                .collect(Collectors.toList());
    }

    // READ BY ID
    public Optional<User> getUserById(String id) {
        return userRepository.findById(id);
    }

    // UPDATE
    public User updateUser(String id, User userRequest) {

        User existingUser = userRepository.findById(id)
                .orElseThrow(() -> new NoSuchElementException("User not found"));

        existingUser.setName(userRequest.getName());
        existingUser.setEmail(userRequest.getEmail());
        existingUser.setUpdatedAt(Instant.now());

        return userRepository.save(existingUser);
    }

    // DELETE
    public boolean deleteUser(String id) {
        if (!userRepository.existsById(id)) {
            return false;
        }
        userRepository.deleteById(id);
        return true;
    }

    // FUZZY SEARCH USERS
    public List<User> searchUsers(String query) {

        try {
            SearchResponse<User> response = elasticsearchClient.search(s -> s
                    .index("users")
                    .size(10)
                    .query(q -> q
                            .bool(b -> b
                                    .minimumShouldMatch("1")
                                    .should(sh -> sh
                                            .match(m -> m
                                                    .field("name")
                                                    .query(query)
                                                    .boost(3.0f)
                                            )
                                    )
                                    .should(sh -> sh
                                            .prefix(p -> p
                                                    .field("name")
                                                    .value(query.toLowerCase())
                                            )
                                    )
                                    .should(sh -> sh
                                            .fuzzy(f -> f
                                                    .field("name")
                                                    .value(query)
                                                    .fuzziness("AUTO")
                                            )
                                    )
                            )
                    ),
                    User.class
            );

            return response.hits()
                    .hits()
                    .stream()
                    .map(hit -> hit.source())
                    .toList();

        } catch (Exception e) {
            throw new RuntimeException("User search failed", e);
        }
    }
}
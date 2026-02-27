package com.example.user.service;

import com.example.user.model.User;
import com.example.user.repository.UserRepository;
import org.springframework.stereotype.Service;
import org.springframework.context.annotation.Lazy;

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

    public UserService(@Lazy UserRepository userRepository) {
        this.userRepository = userRepository;
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
}

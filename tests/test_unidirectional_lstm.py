import torch
import numpy
import pytest

from pytorch_stateful_lstm import UnidirectionalSingleLayerLstm, UnidirectionalLstm
from allennlp.modules.lstm_cell_with_projection import LstmCellWithProjection


def test_unidirectional_single_layer_lstm():
    input_tensor = torch.rand(4, 5, 3)
    input_tensor[1, 4:, :] = 0.
    input_tensor[2, 2:, :] = 0.
    input_tensor[3, 1:, :] = 0.

    initial_hidden_state = torch.ones([1, 4, 5])
    initial_cell_state = torch.ones([1, 4, 7])

    lstm = UnidirectionalSingleLayerLstm(
            input_size=3,
            hidden_size=5,
            cell_size=7,
            cell_clip=2,
            proj_clip=1,
    )
    output_sequence, lstm_state = lstm(
            input_tensor,
            [5, 4, 2, 1],
            (initial_hidden_state, initial_cell_state),
    )
    numpy.testing.assert_array_equal(output_sequence.data[1, 4:, :].numpy(), 0.0)
    numpy.testing.assert_array_equal(output_sequence.data[2, 2:, :].numpy(), 0.0)
    numpy.testing.assert_array_equal(output_sequence.data[3, 1:, :].numpy(), 0.0)

    # Test the state clipping.
    numpy.testing.assert_array_less(output_sequence.data.numpy(), 1.0)
    numpy.testing.assert_array_less(-output_sequence.data.numpy(), 1.0)

    # LSTM state should be (1, batch_size, hidden_size)
    assert list(lstm_state[0].size()) == [1, 4, 5]
    # LSTM memory cell should be (1, batch_size, cell_size)
    assert list((lstm_state[1].size())) == [1, 4, 7]

    # Test the cell clipping.
    numpy.testing.assert_array_less(lstm_state[0].data.numpy(), 2.0)
    numpy.testing.assert_array_less(-lstm_state[0].data.numpy(), 2.0)


def test_unidirectional_single_layer_lstm_initial_state():
    input_tensor = torch.rand(4, 5, 3)

    initial_hidden_state = torch.ones([1, 8, 5])
    initial_cell_state = torch.ones([1, 8, 7])

    lstm = UnidirectionalSingleLayerLstm(
            input_size=3,
            hidden_size=5,
            cell_size=7,
            cell_clip=2,
            proj_clip=1,
    )
    output_sequence, lstm_state = lstm(
            input_tensor,
            [5, 4, 2, 1],
            (initial_hidden_state, initial_cell_state),
    )

    numpy.testing.assert_array_equal(
            initial_hidden_state.data[0, 4:, :].numpy(),
            lstm_state[0].data[0, 4:, :].numpy(),
    )
    numpy.testing.assert_array_equal(
            initial_cell_state.data[0, 4:, :].numpy(),
            lstm_state[1].data[0, 4:, :].numpy(),
    )

    initial_hidden_state = torch.ones([1, 2, 5])
    initial_cell_state = torch.ones([1, 2, 7])
    with pytest.raises(ValueError):
        lstm(
                input_tensor,
                [5, 4, 2, 1],
                (initial_hidden_state, initial_cell_state),
        )


def test_unidirectional_single_layer_lstm_with_allennlp():
    input_tensor = torch.rand(4, 5, 3)
    input_tensor[1, 4:, :] = 0.
    input_tensor[2, 2:, :] = 0.
    input_tensor[3, 1:, :] = 0.

    initial_hidden_state = torch.ones([1, 4, 5])
    initial_cell_state = torch.ones([1, 4, 7])

    for go_forward in [True, False]:

        allennlp_lstm = LstmCellWithProjection(
                input_size=3,
                hidden_size=5,
                cell_size=7,
                go_forward=go_forward,
                memory_cell_clip_value=2,
                state_projection_clip_value=1,
        )
        lstm = UnidirectionalSingleLayerLstm(
                input_size=3,
                hidden_size=5,
                cell_size=7,
                go_forward=go_forward,
                cell_clip=2,
                proj_clip=1,
        )

        lstm.named_parameters()['input_linearity_weight'].data.copy_(
                allennlp_lstm.input_linearity.weight,)
        lstm.named_parameters()['hidden_linearity_weight'].data.copy_(
                allennlp_lstm.state_linearity.weight,)
        lstm.named_parameters()['hidden_linearity_bias'].data.copy_(
                allennlp_lstm.state_linearity.bias,)
        lstm.named_parameters()['proj_linearity_weight'].data.copy_(
                allennlp_lstm.state_projection.weight,)

        output_sequence, lstm_state = lstm(
                input_tensor,
                [5, 4, 2, 1],
                (initial_hidden_state, initial_cell_state),
        )
        allennlp_output_sequence, allennlp_lstm_state = allennlp_lstm(
                input_tensor,
                [5, 4, 2, 1],
                (initial_hidden_state, initial_cell_state),
        )

        numpy.testing.assert_array_equal(output_sequence.data.numpy(),
                                         allennlp_output_sequence.data.numpy())
        numpy.testing.assert_array_equal(lstm_state[0].data.numpy(),
                                         allennlp_lstm_state[0].data.numpy())
        numpy.testing.assert_array_equal(lstm_state[1].data.numpy(),
                                         allennlp_lstm_state[1].data.numpy())


def test_unidirectional_single_layer_lstm_variational_dropout():
    input_tensor = torch.rand(4, 5, 3)
    input_tensor[1, 4:, :] = 0.
    input_tensor[2, 2:, :] = 0.
    input_tensor[3, 1:, :] = 0.

    lstm = UnidirectionalSingleLayerLstm(
            input_size=3,
            hidden_size=50,
            cell_size=7,
            recurrent_dropout_type=1,
            recurrent_dropout_probability=0.1,
    )

    output_sequence_1, lstm_state_1 = lstm(
            input_tensor,
            [5, 4, 2, 1],
    )
    output_sequence_2, lstm_state_2 = lstm(
            input_tensor,
            [5, 4, 2, 1],
    )

    numpy.testing.assert_raises(
            AssertionError,
            numpy.testing.assert_array_equal,
            output_sequence_1.data.numpy(),
            output_sequence_2.data.numpy(),
    )
    numpy.testing.assert_raises(
            AssertionError,
            numpy.testing.assert_array_equal,
            lstm_state_1[0].data.numpy(),
            lstm_state_2[0].data.numpy(),
    )
    numpy.testing.assert_raises(
            AssertionError,
            numpy.testing.assert_array_equal,
            lstm_state_1[1].data.numpy(),
            lstm_state_2[1].data.numpy(),
    )


def test_unidirectional_single_layer_lstm_dropconnect():
    input_tensor = torch.rand(4, 5, 3)
    input_tensor[1, 4:, :] = 0.
    input_tensor[2, 2:, :] = 0.
    input_tensor[3, 1:, :] = 0.

    lstm = UnidirectionalSingleLayerLstm(
            input_size=3,
            hidden_size=50,
            cell_size=7,
            recurrent_dropout_type=2,
            recurrent_dropout_probability=0.1,
    )

    output_sequence_1, lstm_state_1 = lstm(
            input_tensor,
            [5, 4, 2, 1],
    )
    output_sequence_2, lstm_state_2 = lstm(
            input_tensor,
            [5, 4, 2, 1],
    )

    numpy.testing.assert_raises(
            AssertionError,
            numpy.testing.assert_array_equal,
            output_sequence_1.data.numpy(),
            output_sequence_2.data.numpy(),
    )
    numpy.testing.assert_raises(
            AssertionError,
            numpy.testing.assert_array_equal,
            lstm_state_1[0].data.numpy(),
            lstm_state_2[0].data.numpy(),
    )
    numpy.testing.assert_raises(
            AssertionError,
            numpy.testing.assert_array_equal,
            lstm_state_1[1].data.numpy(),
            lstm_state_2[1].data.numpy(),
    )


def test_unidirectional_lstm():
    input_tensor = torch.rand(4, 5, 3)
    input_tensor[1, 4:, :] = 0.
    input_tensor[2, 2:, :] = 0.
    input_tensor[3, 1:, :] = 0.

    initial_hidden_state = torch.ones([2, 4, 5])
    initial_cell_state = torch.ones([2, 4, 7])

    lstm = UnidirectionalLstm(
            num_layers=2,
            input_size=3,
            hidden_size=5,
            cell_size=7,
    )
    output_sequence, lstm_state = lstm(
            input_tensor,
            [5, 4, 2, 1],
            (initial_hidden_state, initial_cell_state),
    )

    assert list(output_sequence.size()) == [2, 4, 5, 5]
    numpy.testing.assert_array_equal(output_sequence.data[0, 1, 4:, :].numpy(), 0.0)
    numpy.testing.assert_array_equal(output_sequence.data[0, 2, 2:, :].numpy(), 0.0)
    numpy.testing.assert_array_equal(output_sequence.data[0, 3, 1:, :].numpy(), 0.0)
    numpy.testing.assert_array_equal(output_sequence.data[1, 1, 4:, :].numpy(), 0.0)
    numpy.testing.assert_array_equal(output_sequence.data[1, 2, 2:, :].numpy(), 0.0)
    numpy.testing.assert_array_equal(output_sequence.data[1, 3, 1:, :].numpy(), 0.0)

    # LSTM state should be (1, batch_size, hidden_size)
    assert list(lstm_state[0].size()) == [2, 4, 5]
    # LSTM memory cell should be (1, batch_size, cell_size)
    assert list((lstm_state[1].size())) == [2, 4, 7]